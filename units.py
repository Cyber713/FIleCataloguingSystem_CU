import os
from enum import Enum
import asyncio
import pymysql


class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"


class Errors(Enum):
    EVERYTHING_IS_FINE = "everything_is_fine"
    AUTH_ERROR = "auth_error"
    CONNECTION_ERROR = "connection_error"
    SOMETHING_WENT_WRONG = "something_went_wrong"


class FileEntry:
    def __init__(
        self, id: int = None, name: str = None, abs_path: str = None, type: FileType = None,
        parent_id: int = None, parent_path: str = None, size: int = None
    ):
        self._id = id
        self._name = name
        self._abs_path = abs_path
        self._type = type
        self._parent_id = parent_id
        self._parent_path = parent_path
        self._size = size

    def __str__(self):
        return (
            f"📂 FileEntry(id={self._id}, name='{self._name}', type={self._type.value},\n"
            f"   path='{self._abs_path}', parent_id={self._parent_id}, parent_path='{self._parent_path}',\n"
            f"   size={'-' if self._size is None else self._size} bytes)"
        )

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def abs_path(self):
        return self._abs_path

    @property
    def type(self):
        return self._type

    @property
    def parent_id(self):
        return self._parent_id

    @property
    def parent_path(self):
        return self._parent_path

    @property
    def size(self):
        return self._size


class DatabaseManager:
    def __init__(self, host: str, port: int, user: str, passwd: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.passwd =passwd
        self.database = database
        self.error_code = Errors.EVERYTHING_IS_FINE
        try:
            self.selfcheck(host, port, user, passwd, database)
            self.connection = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=database)
            self.cursor = self.connection.cursor()
        except pymysql.err.OperationalError as e:
            if e.args[0] == 1045:
                self.error_code = Errors.AUTH_ERROR
            elif e.args[0] == 2003:
                self.error_code = Errors.CONNECTION_ERROR
            else:
                self.error_code = Errors.SOMETHING_WENT_WRONG
        except Exception:
            self.error_code = Errors.SOMETHING_WENT_WRONG

    def fetch_all_files(self):
        print("Fetchiing")
        query = """SELECT f.id, f.name, f.type, f.absolute_path, f.parent_id, f.size, p.absolute_path AS parent_path 
                   FROM Files_And_Directories f 
                   LEFT JOIN Files_And_Directories p ON f.parent_id = p.id;"""
        self.cursor.execute(query)
        return [
            FileEntry(id=row[0], name=row[1], type=FileType(row[2]), abs_path=row[3], parent_id=row[4], size=row[5], parent_path=row[6])
            for row in self.cursor.fetchall()
        ]

    def search_with_keywords(self, keyword_string):
        keywords = keyword_string.split()[:3]
        if not keywords:
            return self.fetch_all_files()

        search_conditions = " OR ".join(["f.name LIKE %s OR f.absolute_path LIKE %s"] * len(keywords))
        query = f"""
        SELECT f.id, f.name, f.type, f.absolute_path, f.parent_id, f.size, p.absolute_path AS parent_path
        FROM Files_And_Directories f
        LEFT JOIN Files_And_Directories p ON f.parent_id = p.id
        WHERE {search_conditions};
        """
        params = [f"%{kw}%" for kw in keywords for _ in range(2)]
        self.cursor.execute(query, params)
        return [
            FileEntry(id=row[0], name=row[1], type=FileType(row[2]), abs_path=row[3], parent_id=row[4], size=row[5], parent_path=row[6])
            for row in self.cursor.fetchall()
        ]

    def insert(self, entry: FileEntry):
        query = """INSERT INTO Files_And_Directories (name, type, parent_id, absolute_path, size) VALUES (%s, %s, %s, %s, %s)"""
        self.cursor.execute(query, (entry.name, entry.type.value, entry.parent_id, entry.abs_path, entry.size))
        self.connection.commit()
        return self.cursor.lastrowid

    async def insert_directory_to_db(self, directory_path: str, parent_id: int = None):
        await asyncio.to_thread(self._insert_directory_to_db, directory_path, parent_id)

    def _insert_directory_to_db(self, directory_path: str, parent_id: int = None):
        """ Inserts a directory and its contents recursively while preventing duplicates """
        self.ensure_connection()
        self.cursor.execute("SELECT id FROM Files_And_Directories WHERE absolute_path = %s", (directory_path,))
        existing = self.cursor.fetchone()

        if existing:
            new_parent_id = existing[0]  # ✅ Use existing ID if directory exists
        else:
            dir_name = os.path.basename(directory_path)
            file_entry = FileEntry(
                name=dir_name,
                abs_path=directory_path,
                type=FileType.DIRECTORY,
                parent_id=parent_id,
                size=None
            )
            new_parent_id = self.insert(file_entry)  # Insert and get new ID

        for entry in os.scandir(directory_path):
            entry_type = FileType.DIRECTORY if entry.is_dir() else FileType.FILE
            entry_size = os.path.getsize(entry.path) if entry.is_file() else None

            # ✅ Check if this entry (file/folder) already exists
            self.ensure_connection()
            self.cursor.execute("SELECT id FROM Files_And_Directories WHERE absolute_path = %s", (entry.path,))
            if self.cursor.fetchone():
                continue  # Skip duplicate entries

            file_entry = FileEntry(
                name=entry.name,
                abs_path=entry.path,
                type=entry_type,
                parent_id=new_parent_id,
                size=entry_size
            )
            child_id = self.insert(file_entry)

            # ✅ Recursively insert subdirectories
            if entry.is_dir():
                 self._insert_directory_to_db(entry.path, child_id)

    def delete_directory(self, parent_id):
        if not parent_id:
            print("Error here")
            return
        self.cursor.execute("SELECT id FROM Files_And_Directories WHERE parent_id = %s", (parent_id,))
        child_ids = [row[0] for row in self.cursor.fetchall()]
        for child_id in child_ids:
            self.delete_directory(child_id)
        self.cursor.execute("DELETE FROM Files_And_Directories WHERE id = %s", (parent_id,))
        print(f"DELETE FROM Files_And_Directories WHERE id = {parent_id}")
        self.connection.commit()

    def update(self, entry: FileEntry):
        query = """UPDATE Files_And_Directories SET name = %s WHERE id = %s"""
        self.cursor.execute(query, (entry.name, entry.id))
        self.connection.commit()

    def delete(self, entry: FileEntry):
        query = """DELETE FROM Files_And_Directories WHERE id = %s"""
        self.cursor.execute(query, (entry.id,))
        self.connection.commit()

    def close(self):
        self.cursor.close()
        self.connection.close()

    def selfcheck(self, host: str, port: int, user: str, passwd: str, database: str):
        test = pymysql.connect(host=host, port=port, user=user, passwd=passwd)
        test_cursor = test.cursor()
        test_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database};")
        test.commit()
        test_cursor.execute(f"USE {database};")
        test_cursor.execute(
            """CREATE TABLE IF NOT EXISTS Files_And_Directories (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL,
                type ENUM('file', 'directory') NOT NULL,
                parent_id INT NULL,
                absolute_path VARCHAR(1024) NOT NULL,
                size BIGINT DEFAULT NULL,
                FOREIGN KEY (parent_id) REFERENCES Files_And_Directories(id),
                INDEX idx_parent_id (parent_id)
            );"""
        )
        test.commit()
        test_cursor.close()
        test.close()

    def ensure_connection(self):
        try:
            self.connection.ping(reconnect=True)
        except pymysql.err.OperationalError:
            print("🔄 Reconnecting to the database...")
            self.connection = pymysql.connect(
                host=self.host, port=self.port, user=self.user, passwd=self.passwd, db=self.database
            )
            self.cursor = self.connection.cursor()

