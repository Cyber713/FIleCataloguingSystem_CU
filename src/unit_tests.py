import hashlib
import unittest
import units


class TestDataBase(unittest.TestCase):
    CORRECT_PASSWORD = "root" # provide your true password to check
    INCORRECT_PASSWORD = "<PASSWORD>"
    TEST_FILE_NAME = "test_file.txt"
    TEST_FILE_ABS_PATH = "/tmp/test_file.txt"

    def test_connection_incorrect_password(self):
        dbm = units.DatabaseManager(host='localhost', port=3306, user='root', passwd=self.INCORRECT_PASSWORD,
                                    database='test')
        self.assertEqual(dbm.error_code, units.Errors.AUTH_ERROR)

    def test_connection_correct_password(self):
        dbm = units.DatabaseManager(host='localhost', port=3306, user='root', passwd=self.CORRECT_PASSWORD,
                                    database='test')
        self.assertEqual(dbm.error_code, units.Errors.EVERYTHING_IS_FINE)

    def test_path_hash_consistency(self):
        dbm = units.DatabaseManager(host='localhost', port=3306, user='root', passwd=self.CORRECT_PASSWORD,
                                    database='test')
        path = self.TEST_FILE_ABS_PATH
        hash1 = dbm.hash_path(path)
        self.assertEqual(hash1, hashlib.sha256(path.encode()).hexdigest())

    def test_insert_and_fetch(self):
        dbm = units.DatabaseManager(host='localhost', port=3306, user='root', passwd=self.CORRECT_PASSWORD,
                                    database='test')

        test_entry = units.FileEntry(
            name=self.TEST_FILE_NAME,
            abs_path=self.TEST_FILE_ABS_PATH,
            type=units.FileType.FILE,
            parent_id=None,
            size=1234,
            abs_path_hash=dbm.hash_path(self.TEST_FILE_ABS_PATH)
        )

        inserted_id = dbm.insert(test_entry)
        self.assertIsNotNone(inserted_id)
        all_files = dbm.fetch_all_files()
        result_check = any(file.abs_path_hash == dbm.hash_path(self.TEST_FILE_ABS_PATH) for file in all_files)
        self.assertTrue(result_check)

    def test_search_with_keyword(self):
        dbm = units.DatabaseManager(host='localhost', port=3306, user='root', passwd=self.CORRECT_PASSWORD,
                                    database='test')

        keyword = 'test_file'
        results = dbm.search_with_keywords(keyword)

        print(keyword in results[0].name)

        check = any(keyword in file.name for file in results)
        self.assertTrue(check)

        dbm.cursor.execute(
            "DELETE FROM Files_And_Directories WHERE absolute_path_hash = %s",
            [dbm.hash_path(self.TEST_FILE_ABS_PATH)]
        )
        dbm.connection.commit()


if __name__ == '__main__':
    tester = TestDataBase()
