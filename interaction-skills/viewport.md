# Viewport

Use viewport helpers when screenshots, layout, or responsive behavior matter.

## Set viewport

```python
set_viewport(1366, 768)
wait(0.5)
print(page_info())
```

## Capture screenshot

```python
capture_screenshot("/tmp/viewport.png")
capture_screenshot("/tmp/full-page.png", full=True)
```

## Print to PDF

```python
print_pdf("/tmp/page.pdf")
```

`print_pdf()` uses `browsingContext.print`; support can vary by browser and driver version.
