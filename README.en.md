# Triangulum Daily

English | [中文](https://github.com/qianqian5774/triangulum-daily3albums/tree/main)

Nine albums a day.
Three release windows, three albums at a time.
No endless feed or chart-chasing—just a few daily openings into somewhere less familiar. 🎧

## 🌗 What is this?

**Triangulum Daily** is a music discovery project that recommends nine albums every day.

It began as a personal listening ritual: a place where albums could sit slightly outside streaming feeds and systems that keep pointing back to the same familiar corners. There is no infinite scroll and no attempt to continuously predict what you already like. The nine daily albums arrive in three releases, giving the site the rhythm of a small music calendar.

The site generates its content automatically, unlocks it progressively in Beijing time, and keeps previous recommendations as a static archive.

## ✨ What it does

Every day, the site presents nine album recommendations. Three albums unlock in each release window:

| Time  | Release                      |
| ----- | ---------------------------- |
| 08:00 | First window, three albums   |
| 12:30 | Second window, three albums  |
| 16:00 | Third window, three albums   |

Before 08:00, the Today Page remains in its normal Offline State. When the next window arrives, three more albums become available.

This is not designed to be the most popular, authoritative, or personalized recommendation engine. It is closer to a daily listening prompt: sometimes familiar, sometimes unexpected, and ideally just far enough away from your usual path.

## 🧭 Why it exists

Music is easier to access than ever, but discovery can still feel strangely narrow.

You may keep returning to the same artists, moods, or recommendation patterns. Triangulum Daily is a small attempt to loosen that loop.

It cares about:

- Unlocking only three albums at a time instead of creating another wall of content.
- Keeping some distance from the obvious and overexposed.
- Building an archive that can be revisited over time.
- Treating music discovery more like a walk than a feed.

## 🕰 Daily rhythm

Triangulum Daily follows Beijing time.

```text
00:00 - 07:59   Offline State
08:00 - 12:29   First window
12:30 - 15:59   Second window
16:00 - 23:59   Third window
```

The three windows are not meant to manufacture mystery. They give the site a clear, finite rhythm.

## 🗂 What you will find

- **Today Page** — nine albums unlocked across three release windows.
- **Treatment Viewer** — an overlay opened from an Album Card, not a standalone detail route.
- **Archive Page** — previous daily recommendations stored as static data.
- **Share Card** — a downloadable card based on the windows unlocked so far.
- **Ambient Overlay** — an immersive or standby view.

## ⚙️ How it works

Each morning, the Python generator reads configuration and external music data, produces nine recommendations and static JSON, and combines them with the React/Vite UI for deployment on GitHub Pages.

```text
external music data → Python generator → static JSON → React/Vite UI → GitHub Pages
```

Visitors do not need a live backend, and their browsers do not call external music APIs to generate recommendations.

## 🌐 Live site

[triangulumdaily.space](https://triangulumdaily.space/)

The repository name `triangulum-daily3albums` remains unchanged for now so the product-name migration does not expand into package, link, and deployment-path changes.

## 📌 Current priorities

- Keeping daily generation, archive recovery, and publishing continuous.
- Measuring deployment margin before the 08:00 unlock.
- Establishing a baseline for lower-performance devices.
- Clarifying which recommendation configuration is active at runtime.

---

Made for slower listening.

One day, nine albums. Three at a time.
