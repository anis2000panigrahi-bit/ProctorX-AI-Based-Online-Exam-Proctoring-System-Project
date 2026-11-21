import random

MCQ_BANK = [

    {
        "id": "py1",
        "question": "Which keyword is used to define a function in Python?",
        "options": [
            "function",
            "define",
            "def",
            "fun"
        ],
        "answer": "def"
    },

    {
        "id": "py2",
        "question": "Which data type is used to store True or False values?",
        "options": [
            "int",
            "bool",
            "str",
            "float"
        ],
        "answer": "bool"
    },

    {
        "id": "py3",
        "question": "What is the output of print(2 ** 3)?",
        "options": [
            "6",
            "8",
            "9",
            "5"
        ],
        "answer": "8"
    },

    {
        "id": "py4",
        "question": "Which method is used to add an element to the end of a list?",
        "options": [
            "add()",
            "insert()",
            "append()",
            "extend()"
        ],
        "answer": "append()"
    },

    {
        "id": "py5",
        "question": "Which symbol is used for single-line comments in Python?",
        "options": [
            "//",
            "#",
            "/*",
            "--"
        ],
        "answer": "#"
    },

    {
        "id": "py6",
        "question": "What is the output of len('Python')?",
        "options": [
            "5",
            "6",
            "7",
            "8"
        ],
        "answer": "6"
    },

    {
        "id": "py7",
        "question": "Which loop is used to iterate over a sequence in Python?",
        "options": [
            "repeat",
            "foreach",
            "for",
            "loop"
        ],
        "answer": "for"
    },

    {
        "id": "py8",
        "question": "Which of the following is an immutable data type in Python?",
        "options": [
            "List",
            "Dictionary",
            "Set",
            "Tuple"
        ],
        "answer": "Tuple"
    },

    {
        "id": "py9",
        "question": "What is the output of print(10 // 3)?",
        "options": [
            "3.33",
            "3",
            "1",
            "4"
        ],
        "answer": "3"
    },

    {
        "id": "py10",
        "question": "Which keyword is used to handle exceptions in Python?",
        "options": [
            "catch",
            "error",
            "try",
            "excepted"
        ],
        "answer": "try"
    },

    {
        "id": "py11",
        "question": "Which function is used to display output in Python?",
        "options": [
            "display()",
            "print()",
            "show()",
            "output()"
        ],
        "answer": "print()"
    },

    {
        "id": "py12",
        "question": "Which operator is used for equality comparison in Python?",
        "options": [
            "=",
            "==",
            "!=",
            ">="
        ],
        "answer": "=="
    },

    {
        "id": "py13",
        "question": "What is the output of print(5 % 2)?",
        "options": [
            "2",
            "2.5",
            "1",
            "0"
        ],
        "answer": "1"
    },

    {
        "id": "py14",
        "question": "Which collection stores data in key-value pairs?",
        "options": [
            "List",
            "Tuple",
            "Dictionary",
            "Set"
        ],
        "answer": "Dictionary"
    },

    {
        "id": "py15",
        "question": "Which keyword is used to create a class in Python?",
        "options": [
            "object",
            "class",
            "struct",
            "define"
        ],
        "answer": "class"
    },

    {
        "id": "py16",
        "question": "What is the output of print(type(10))?",
        "options": [
            "<class 'str'>",
            "<class 'float'>",
            "<class 'int'>",
            "<class 'bool'>"
        ],
        "answer": "<class 'int'>"
    },

    {
        "id": "py17",
        "question": "Which function converts a string into an integer?",
        "options": [
            "str()",
            "float()",
            "int()",
            "bool()"
        ],
        "answer": "int()"
    },

    {
        "id": "py18",
        "question": "Which statement is used to stop a loop immediately?",
        "options": [
            "skip",
            "stop",
            "break",
            "continue"
        ],
        "answer": "break"
    },

    {
        "id": "py19",
        "question": "What is the output of print(3 * 'Hi')?",
        "options": [
            "Hi3",
            "HiHiHi",
            "HHH",
            "Error"
        ],
        "answer": "HiHiHi"
    },

    {
        "id": "py20",
        "question": "Which module provides mathematical functions in Python?",
        "options": [
            "random",
            "math",
            "os",
            "sys"
        ],
        "answer": "math"
    }

]


LONG_BANK = [

    {
        "id": "l1",
        "question": "Explain the difference between a stack and a queue. Include one real-world example of each."
    },

    {
        "id": "l2",
        "question": "Explain the four main principles of object-oriented programming with brief examples."
    },

    {
        "id": "l3",
        "question": "Describe database normalization and explain 1NF, 2NF and 3NF."
    },

    {
        "id": "l4",
        "question": "Explain binary search, its working steps, and its time complexity. Mention its prerequisite."
    },

    {
        "id": "l5",
        "question": "Describe the software development life cycle (SDLC) and explain any four phases."
    },

    {
        "id": "l6",
        "question": "What is process scheduling in an operating system? Explain FCFS and Round Robin scheduling."
    },

    {
        "id": "l7",
        "question": "Explain how a Flask application handles a browser request and returns an HTML response."
    },

    {
        "id": "l8",
        "question": "Explain the difference between supervised, unsupervised and reinforcement learning with examples."
    },

    {
        "id": "l9",
        "question": "Describe SQL joins and compare INNER JOIN, LEFT JOIN and RIGHT JOIN."
    },

    {
        "id": "l10",
        "question": "Explain recursion and backtracking. Use one suitable algorithm as an example."
    }

]