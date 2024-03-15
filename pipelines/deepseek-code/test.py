import unittest
import os
from pipeline import find_local_imports  # Adjust the import path as necessary

class TestLocalImports(unittest.TestCase):
    test_dir = "test_dir"
    
    @classmethod
    def setUpClass(cls):
        # Set up a temporary directory with test Python files
        os.makedirs(cls.test_dir, exist_ok=True)
        cls.create_test_file('module1.py', '')
        cls.create_test_file('module2.py', 'import module1 \nimport asyncio')
        cls.create_test_file('subdir/module3.py', 'from .. import module2')
    
    @classmethod
    def tearDownClass(cls):
        # Clean up the directory after tests
        for root, dirs, files in os.walk(cls.test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(cls.test_dir)
    
    @classmethod
    def create_test_file(cls, filename, content):
        path = os.path.join(cls.test_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
    
    def test_find_local_imports(self):
        # This is a basic test. You should expand it based on your function's capabilities
        imports = find_local_imports(self.test_dir)
        self.assertIn(os.path.join(self.test_dir, 'module2.py'), imports)
        self.assertIn('module1', imports[os.path.join(self.test_dir, 'module2.py')])
        
        # Test for relative imports in subdirectories
        module3_path = os.path.join(self.test_dir, 'subdir/module3.py')
        self.assertIn(module3_path, imports)
        self.assertTrue(any('module2' in imp for imp in imports[module3_path]))

if __name__ == '__main__':
    unittest.main()
