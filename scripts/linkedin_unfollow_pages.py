"""
Unfollow all LinkedIn pages EXCEPT a small allow-list (Ameza, Mindful).

Flow:
  1. Opens a visible Chromium window.
  2. You log in (and complete 2FA) manually.
  3. Press ENTER in the terminal when logged in.
  4. Script navigates to https://www.linkedin.com/feed/following/
  5. For each followed entity it scans the entity name and the entity's
     "Following" button. If the name does NOT contain any allow-list keyword
     (case-insensitive), the button is clicked and any confirmation modal
     is dismissed with "Unfollow" / "Remove" / primary action.
  6. Every action is logged to unfollowed_pages.log.

Allow-list is at the top of the file — edit there if you want to keep more.
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, ElementHandle

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "unfollowed_pages.log"

FOLLOWING_URL = "https://www.linkedin.com/mynetwork/network-manager/company/"

# Pages to KEEP following — case-insensitive substring match against entity name.
ALLOW_LIST = [
    "ameza",
    "mindful",
]


def is_allowed(name: str) -> bool:
    low = (name or "").lower()
    return any(k in low for k in ALLOW_LIST)


def log(line: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {line}"
    print(msg)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


async def ask(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(None, input, prompt)).strip().lower()


# Each followed entity has a "Following" button. We discover them by their
# aria-label which typically reads "Unfollow <Name>" or "Following <Name>".
# Some variations use just "Following" text — we handle both.
CARD_DISCOVERY_JS = r"""
() => {
  const main = document.querySelector('main') || document.body;
  const buttons = Array.from(main.querySelectorAll('button'));
  const cards = [];
  for (const b of buttons) {
    const aria = (b.getAttribute('aria-label') || '').trim();
    // exact pattern on network-manager/company:
    //   aria-label="Click to stop following <Name>"
    // also handle older variants.
    const patterns = [
      /^Click to stop following\s+(.+?)\s*$/i,
      /^Stop following\s+(.+?)\s*$/i,
      /^Unfollow\s+(.+?)\s*$/i,
      /click to unfollow\s+(.+?)\s*$/i,
    ];
    let name = '';
    for (const re of patterns) {
      const m = aria.match(re);
      if (m) { name = m[1].trim(); break; }
    }
    if (!name) continue;

    if (!b.dataset.unfId) {
      b.dataset.unfId = 'uf_' + Math.random().toString(36).slice(2, 10);
    }
    cards.push({ id: b.dataset.unfId, name: name });
  }
  return cards;
}
"""


async def highlight(el: ElementHandle, color: str = "red") -> None:
    try:
        await el.evaluate(
            "(e, c) => { e.style.outline = '3px solid ' + c; e.style.outlineOffset = '2px'; }",
            color,
        )
        await el.scroll_into_view_if_needed()
    except Exception:
        pass


async def click_unfollow(page: Page, btn: ElementHandle, name: str) -> bool:
    """Click Following button; if a confirmation modal appears, click Unfollow."""
    try:
        await btn.scroll_into_view_if_needed()
        await btn.click()
        await page.wait_for_timeout(200)

        # Some unfollows are immediate; some open a modal asking confirmation.
        # Try to find a confirmation button — if not found in 1s, assume direct.
        ok = await page.evaluate(r"""
        () => {
          const btns = Array.from(document.querySelectorAll('button'));
          // candidate confirmation: text is exactly "Unfollow" and has a Cancel sibling.
          const unfBtns = btns.filter(b => /^unfollow$/i.test((b.innerText||b.textContent||'').trim()));
          for (const ub of unfBtns) {
            let p = ub.parentElement;
            for (let i = 0; i < 6 && p; i++, p = p.parentElement) {
              const cancel = Array.from(p.querySelectorAll('button')).find(b =>
                /^cancel$/i.test((b.innerText||b.textContent||'').trim())
              );
              if (cancel) {
                ub.click();
                return 'modal';
              }
            }
          }
          return 'no-modal';
        }
        """)
        return True if ok else False
    except Exception as e:
        log(f"  ! unfollow failed for {name}: {e}")
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def scroll_to_load_more(page: Page) -> bool:
    """Try several scroll strategies and click any 'Show more' button. Returns
    True if any new content appeared (height grew or button count grew)."""
    before = await page.evaluate(r"""
    () => ({
      h: document.body.scrollHeight,
      btns: document.querySelectorAll('button[aria-label^="Click to stop following"]').length,
    })
    """)

    # 1) window scroll to absolute bottom
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(400)
    # 2) keyboard End — sometimes triggers virtualised lists
    try:
        await page.keyboard.press("End")
    except Exception:
        pass
    await page.wait_for_timeout(400)
    # 3) scroll any inner scrollable container that contains a Following button
    await page.evaluate(r"""
    () => {
      const btn = document.querySelector('button[aria-label^="Click to stop following"]');
      if (!btn) return;
      let p = btn.parentElement;
      while (p && p !== document.body) {
        const cs = getComputedStyle(p);
        if ((cs.overflowY === 'auto' || cs.overflowY === 'scroll') && p.scrollHeight > p.clientHeight) {
          p.scrollTop = p.scrollHeight;
          break;
        }
        p = p.parentElement;
      }
    }
    """)
    await page.wait_for_timeout(800)
    # 4) click any "Show more" / "See more" button
    try:
        more = page.locator(
            "button:has-text('Show more'), button:has-text('See more'), button:has-text('Load more'), button:has-text('Daha fazla')"
        ).first
        if await more.is_visible(timeout=500):
            await more.click()
            await page.wait_for_timeout(800)
    except Exception:
        pass

    after = await page.evaluate(r"""
    () => ({
      h: document.body.scrollHeight,
      btns: document.querySelectorAll('button[aria-label^="Click to stop following"]').length,
    })
    """)
    return after["h"] > before["h"] or after["btns"] > before["btns"]


async def run() -> None:
    log(f"=== session start, log file: {LOG_PATH} ===")
    log(f"allow-list (kept): {ALLOW_LIST}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(viewport=None)
        page = await context.new_page()

        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        print("\n>>> LinkedIn login sayfası açıldı.")
        print(">>> Manuel login + 2FA tamamlayın, anasayfaya geldiğinizde terminale dönün.")
        await ask(">>> Login bitince ENTER'a basın... ")

        await page.goto(FOLLOWING_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        log("following page loaded")

        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        processed = 0
        removed = 0
        kept = 0
        idle_scrolls = 0

        while True:
            cards = await page.evaluate(CARD_DISCOVERY_JS)
            if processed == 0 and not cards:
                diag = await page.evaluate(r"""
                () => {
                  const main = document.querySelector('main') || document.body;
                  const btns = main.querySelectorAll('button');
                  const sample = Array.from(btns).slice(0, 20).map(b => ({
                    text: (b.innerText||b.textContent||'').trim().slice(0,40),
                    aria: b.getAttribute('aria-label') || '',
                  }));
                  return { buttonCount: btns.length, sample };
                }
                """)
                log(f"DIAG: {diag}")

            new_in_pass = 0
            for c in cards:
                cid = c["id"]
                name = c["name"]
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                if name in seen_names:
                    continue
                seen_names.add(name)
                new_in_pass += 1
                processed += 1

                if is_allowed(name):
                    log(f"KEEP [{processed}]: {name}")
                    kept += 1
                    continue

                btn = await page.query_selector(f"button[data-unf-id='{cid}']")
                if not btn:
                    log(f"  ! button vanished: {name}")
                    continue

                await highlight(btn, "red")
                log(f"UNFOLLOW [{processed}]: {name}")
                ok = await click_unfollow(page, btn, name)
                if ok:
                    removed += 1
                    log(f"DONE ({removed}): {name}")
                else:
                    log(f"FAILED: {name}")
                await page.wait_for_timeout(random.randint(500, 900))

            if new_in_pass == 0:
                grew = await scroll_to_load_more(page)
                if not grew:
                    idle_scrolls += 1
                    log(f"idle scroll {idle_scrolls}/8 — total processed so far {processed}")
                    if idle_scrolls >= 8:
                        log(f"done. processed={processed} unfollowed={removed} kept={kept}")
                        break
                else:
                    idle_scrolls = 0
            else:
                await scroll_to_load_more(page)
                idle_scrolls = 0

        print("\n>>> Bitti. Pencereyi kapatabilirsiniz.")
        await ask(">>> ENTER ile çık... ")
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
