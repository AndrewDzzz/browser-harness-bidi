# Uploads

Use `upload_file()` for file inputs. It evaluates the selector, obtains a BiDi node reference, and calls `input.setFiles`.

## Single file

```python
upload_file("input[type='file']", "/absolute/path/file.pdf")
```

## Multiple files

```python
upload_file("input[type='file']", ["/absolute/path/a.png", "/absolute/path/b.png"])
```

If the file input is hidden behind a button, inspect the DOM with `js()` or use the visible button first to open the upload state, then call `upload_file()` on the actual input.
