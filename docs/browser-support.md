# Browser support

Status as of 2026-05-25. WebDriver bidi support moves quickly, so treat this as the project support matrix rather than a permanent browser guarantee.

| Browser | bidi status | How this harness connects | Project stance |
|---|---|---|---|
| Firefox Desktop | First-class | `bidi-firefox`, direct `BIDI_WS=ws://127.0.0.1:PORT/session`, or `geckodriver` with `webSocketUrl=true` | Recommended default and best-tested path |
| Chrome Desktop | Supported through ChromeDriver/WebDriver bidi | `bidi-chrome` or `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=chrome` | Supported through the WebDriver bidi path |
| Chromium Desktop | Supported through Chromium/ChromeDriver-compatible WebDriver bidi stacks | `bidi-chrome --chrome-binary ...`, `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=chrome`, or browser-specific capabilities | Expected to work when the driver returns `webSocketUrl`; less tested than Firefox |
| Microsoft Edge Desktop | Expected via EdgeDriver/WebDriver bidi because Edge is Chromium-based, but not verified in this repo yet | `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=edge` with Edge capabilities | Experimental until we add an Edge smoke test |
| Safari / safaridriver | Not a supported target for this harness today | None | Track WebKit/Safari progress; do not promise support yet |
| Mobile browsers | Not supported by this harness today | None | Future work; likely requires Appium/cloud-provider-specific bidi support |

## References

- [MDN: Create a WebDriver bidi connection](https://developer.mozilla.org/en-US/docs/Web/WebDriver/How_to/Create_BiDi_connection)
- [MDN: webSocketUrl capability](https://developer.mozilla.org/en-US/docs/Web/WebDriver/Reference/Capabilities/webSocketUrl)
- [ChromeDriver docs](https://developer.chrome.com/docs/chromedriver?hl=en)
- [Puppeteer WebDriver bidi support](https://pptr.dev/webdriver-bidi)
- [WebKit bidi meta bug](https://www2.webkit.org/show_bug.cgi?id=281932)
