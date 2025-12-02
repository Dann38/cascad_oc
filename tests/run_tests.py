"""
Основной скрипт для запуска всех тестов.
"""
import unittest
import sys
import os

def run_all_tests():
    """Запускает все тесты в проекте"""
    # Добавляем корневую директорию в путь
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_root)
    
    # Находим все тесты
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Запускаем тесты
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Возвращаем код успеха/ошибки
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_all_tests())