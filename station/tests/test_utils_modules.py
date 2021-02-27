import unittest
from types import ModuleType

from utils import modules as moduleUtils


class TestUtilsModules(unittest.TestCase):
    def test_find_exist_function_in_module(self):
        import quality_ratings.analog as module
        function = moduleUtils.get_function_in_module(module, "rate")
        self.assertIsNotNone(function)
        self.assertTrue(callable(function))
        self.assertEquals(function.__name__, "rate")

    def test_find_non_exist_function_in_module(self):
        import quality_ratings.analog as module
        function = moduleUtils.get_function_in_module(module, "foo")
        self.assertIsNone(function)

    def test_find_exist_module_in_directory(self):
        module = moduleUtils.get_module_in_directory("quality_ratings", "analog")
        self.assertIsNotNone(module)
        self.assertEquals(module.__name__, "quality_ratings.analog")
        self.assertIsInstance(module, ModuleType)

    def test_find_non_exist_module_in_directory(self):
        module = moduleUtils.get_module_in_directory("quality_ratings", "foo")
        self.assertIsNone(module)

    def test_list_modules_in_directory(self):
        modules = moduleUtils.get_modules_in_directory("quality_ratings")
        modules = list(modules)
        self.assertGreater(len(modules), 0)        
        for module in modules:
            self.assertIsNotNone(module)
            self.assertTrue(module.__name__.startswith("quality_ratings."))
            self.assertIsInstance(module, ModuleType)

    def test_list_modules_in_not_exist_directory(self):
        iterator = moduleUtils.get_modules_in_directory("foo")
        self.assertRaises(FileNotFoundError, list, iterator)

    def test_find_exist_function_in_directory(self):
        entry = moduleUtils.get_function_in_directory(
            "quality_ratings", "analog", "rate"
        )
        self.assertIsNotNone(entry)
        if entry is not None:
            function, module = entry
            self.assertIsNotNone(function)
            self.assertTrue(callable(function))
            self.assertEquals(function.__name__, "rate")
            self.assertIsNotNone(module)
            self.assertEquals(module.__name__, "quality_ratings.analog")
            self.assertIsInstance(module, ModuleType)
    
    def test_list_functions_in_directory(self):
        entries = moduleUtils.get_functions_in_directory(
            "quality_ratings", "rate"
        )
        entries = list(entries)

        for function, module in entries:
            self.assertIsNotNone(function)
            self.assertTrue(callable(function))
            self.assertEquals(function.__name__, "rate")
            self.assertIsNotNone(module)
            self.assertIsInstance(module, ModuleType)

    def test_list_module_names_with_specific_function_in_directory(self):
        names = moduleUtils.get_names_of_modules_with_function_in_directory(
            "quality_ratings", "rate"
        )
        names = list(names)
        self.assertGreater(len(names), 0)
        for name in names:
            self.assertIsInstance(name, str)
