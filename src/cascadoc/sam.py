"""
Анализатор структуры проекта.
Показывает все файлы, классы и функции с их описаниями.
"""
import os
import ast
import inspect
from typing import Dict, List, Tuple
import importlib.util
import sys

def analyze_project(directory: str = ".", exclude_dirs: List[str] = None) -> str:
    """
    Анализирует структуру проекта и возвращает форматированный отчет.
    
    Args:
        directory: Корневая директория для анализа
        exclude_dirs: Список директорий для исключения
    
    Returns:
        str: Форматированный отчет о структуре проекта
    """
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', '.ipynb_checkpoints']
    
    result = []
    result.append("=" * 80)
    result.append("СТРУКТУРА ПРОЕКТА")
    result.append("=" * 80)
    
    # Собираем все Python файлы
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Исключаем нежелательные директории
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                full_path = os.path.join(root, file)
                python_files.append(full_path)
    
    # Анализируем каждый файл
    for file_path in sorted(python_files):
        file_info = analyze_file(file_path, directory)
        if file_info:
            result.extend(file_info)
            result.append("")  # Пустая строка между файлами
    
    return "\n".join(result)

def analyze_file(file_path: str, base_dir: str) -> List[str]:
    """
    Анализирует один Python файл и возвращает информацию о его содержимом.
    
    Args:
        file_path: Путь к файлу
        base_dir: Базовая директория проекта
    
    Returns:
        List[str]: Список строк с информацией о файле
    """
    result = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим AST
        tree = ast.parse(content)
        
        # Получаем относительный путь
        rel_path = os.path.relpath(file_path, base_dir)
        
        # Добавляем заголовок файла
        result.append(f"ФАЙЛ: {rel_path}")
        result.append("-" * 60)
        
        # Извлекаем модуль-документацию
        module_doc = ast.get_docstring(tree)
        if module_doc:
            # Берем первую строку документации
            first_line = module_doc.strip().split('\n')[0]
            result.append(f"Описание: {first_line}")
        else:
            result.append("Описание: нет документации")
        
        result.append("")
        
        # Ищем классы
        classes = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = analyze_class(node)
                if class_info:
                    classes.append(class_info)
        
        # Ищем функции верхнего уровня
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_info = analyze_function(node)
                if func_info:
                    functions.append(func_info)
        
        # Выводим классы
        if classes:
            result.append("КЛАССЫ:")
            for class_name, init_args, class_doc in classes:
                result.append(f"  📦 {class_name}({init_args})")
                if class_doc:
                    result.append(f"      📝 {class_doc}")
                result.append("")
        
        # Выводим функции
        if functions:
            result.append("ФУНКЦИИ:")
            for func_name, func_args, func_doc in functions:
                result.append(f"  🔧 {func_name}({func_args})")
                if func_doc:
                    result.append(f"      📝 {func_doc}")
                result.append("")
        
        if not classes and not functions:
            result.append("(нет классов или функций верхнего уровня)")
            result.append("")
        
    except Exception as e:
        result.append(f"Ошибка при анализе файла {file_path}: {e}")
        result.append("")
    
    return result

def analyze_class(class_node: ast.ClassDef) -> Tuple[str, str, str]:
    """
    Анализирует класс и возвращает информацию о нем.
    
    Args:
        class_node: AST узел класса
        
    Returns:
        Tuple: (имя_класса, аргументы_init, документация)
    """
    class_name = class_node.name
    
    # Извлекаем документацию класса
    class_doc = ast.get_docstring(class_node)
    if class_doc:
        class_doc = class_doc.strip().split('\n')[0]
    
    # Ищем метод __init__ для получения аргументов
    init_args = []
    for node in class_node.body:
        if (isinstance(node, ast.FunctionDef) and 
            node.name == '__init__' and 
            node.args.args):
            
            # Извлекаем аргументы, кроме 'self'
            for arg in node.args.args:
                if arg.arg != 'self':
                    init_args.append(arg.arg)
            
            # Добавляем *args если есть
            if node.args.vararg:
                init_args.append('*' + node.args.vararg.arg)
            
            # Добавляем **kwargs если есть
            if node.args.kwarg:
                init_args.append('**' + node.args.kwarg.arg)
            
            break
    
    args_str = ", ".join(init_args) if init_args else ""
    
    return class_name, args_str, class_doc or ""

def analyze_function(func_node: ast.FunctionDef) -> Tuple[str, str, str]:
    """
    Анализирует функцию и возвращает информацию о ней.
    
    Args:
        func_node: AST узел функции
        
    Returns:
        Tuple: (имя_функции, аргументы, документация)
    """
    func_name = func_node.name
    
    # Извлекаем документацию функции
    func_doc = ast.get_docstring(func_node)
    if func_doc:
        func_doc = func_doc.strip().split('\n')[0]
    
    # Извлекаем аргументы
    args = []
    for arg in func_node.args.args:
        args.append(arg.arg)
    
    # Добавляем *args если есть
    if func_node.args.vararg:
        args.append('*' + func_node.args.vararg.arg)
    
    # Добавляем **kwargs если есть  
    if func_node.args.kwarg:
        args.append('**' + func_node.args.kwarg.arg)
    
    args_str = ", ".join(args)
    
    return func_name, args_str, func_doc or ""

def get_project_summary(directory: str = ".") -> str:
    """
    Возвращает краткую сводку по проекту.
    
    Args:
        directory: Корневая директория проекта
        
    Returns:
        str: Краткая сводка
    """
    python_files = []
    classes_count = 0
    functions_count = 0
    
    exclude_dirs = ['__pycache__', '.git', '.ipynb_checkpoints']
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                python_files.append(os.path.join(root, file))
    
    # Анализируем статистику
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    classes_count += 1
                elif isinstance(node, ast.FunctionDef):
                    functions_count += 1
                    
        except:
            continue
    
    summary = [
        "=" * 50,
        "СВОДКА ПРОЕКТА",
        "=" * 50,
        f"📁 Всего файлов .py: {len(python_files)}",
        f"📦 Всего классов: {classes_count}",
        f"🔧 Всего функций: {functions_count}",
        "=" * 50
    ]
    
    return "\n".join(summary)

# Функции для удобного использования в Jupyter Notebook
def show_project_structure(directory: str = "."):
    """Показывает структуру проекта в Jupyter Notebook"""
    print(analyze_project(directory))

def show_project_summary(directory: str = "."):
    """Показывает сводку по проекту в Jupyter Notebook"""
    print(get_project_summary(directory))

# Пример использования
if __name__ == "__main__":
    # Показываем сводку
    print(get_project_summary())
    print("\n\n")
    
    # Показываем полную структуру
    print(analyze_project())