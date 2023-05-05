# Interpreter for URL string

We develop a multi-language interpreter to extract abusive endpoints scattering over the AIMIE services.

## Environment

This code runs in a Python3 environment.

```
pip install tree_sitter
pip install colorlog
pip install tldextract
pip install pandas
```

```
mkdir vendor
cd vendor
git clone https://github.com/tree-sitter/tree-sitter-python
git clone https://github.com/tree-sitter/tree-sitter-javascript
git clone https://github.com/tree-sitter/tree-sitter-go
git clone https://github.com/tree-sitter/tree-sitter-java
git clone https://github.com/tree-sitter/tree-sitter-php
```

## Try Interpreter

We have developed an interpreter that can automatically identify upload-related URLs from files or code repositories, covering five different programming languages. They are `py`, `js`, `php`, `java`, `go`.

You can use these interpreters by passing the file name as a parameter, and they will return the upload-related URLs within it.

```
python py_interpreter.py <Python-filename>
python js_interpreter.py <JavaScript-filename>
python php_interpreter.py <PHP-filename>
python java_interpreter.py <Java-filename>
python go_interpreter.py <Go-filename>
```