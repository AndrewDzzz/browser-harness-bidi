# GitHub repository basics

Use this for public GitHub repository pages.

## Loaded state

A repository page is usually ready when one of these exists:

```python
wait_for_element("strong[itemprop='name']", timeout=10)
# or
wait_for_text("Code", timeout=10)
```

## Useful reads

```python
repo_name = get_text("strong[itemprop='name']")
about = get_text("[data-testid='repository-details']") if exists("[data-testid='repository-details']") else None
readme = get_text("article.markdown-body") if exists("article.markdown-body") else None
```

## Common actions

```python
click_selector("a[href$='/issues']")
click_selector("a[href$='/pulls']")
```

## Auth wall

If GitHub asks for sign-in or 2FA, stop and ask the user. Do not type credentials from screenshots.
