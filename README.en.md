# Triangulum Daily 3 Albums

English | [中文](https://github.com/qianqian5774/triangulum-daily3albums/edit/main/README.md)

Three albums a day.
No endless feed, no chart-chasing, no rush to hear everything.
Just three small doors into music, opening throughout the day. 🎧

## 🌗 What is this?

**Triangulum Daily 3 Albums** is a daily music discovery project that recommends three albums every day.

It began as a personal listening ritual. I wanted a place that could gently pull me away from streaming feeds, social media loops, and recommendation systems that often keep pointing back to the same familiar corners.

Instead of an infinite scroll, the site offers only three albums a day. They appear slowly, at fixed moments, and remain archived over time.

You can open it in the morning, come back at noon, check again in the evening, or browse older days later. It is meant to feel less like a feed and more like a small music calendar.

## ✨ What it does

Every day, the site presents three album recommendations.

They are unlocked according to Beijing time:

| Time  | Album        |
| ----- | ------------ |
| 06:00 | First album  |
| 12:00 | Second album |
| 18:00 | Third album  |

Before the day begins, the page stays in a waiting state.
When the next slot arrives, another album appears.

This is not designed to be the most popular, the most authoritative, or the most personalized recommendation engine. It is closer to a daily listening prompt: sometimes familiar, sometimes unexpected, and ideally just far enough away from your usual path.

## 🧭 Why it exists

Music is easier to access than ever, but discovery can still feel strangely narrow.

You may keep returning to the same artists, the same moods, or the same recommendation patterns. Triangulum Daily 3 Albums is a small attempt to make that loop a little looser.

It cares about:

- Fewer recommendations, not more.
- A slower rhythm instead of instant overload.
- A slight distance from the obvious and overexposed.
- A growing archive of past days.
- Music discovery as a walk, not a feed.

## 🕰 Daily rhythm

The site follows Beijing time.

```text
00:00 - 05:59   Today’s albums are not open yet
06:00 - 11:59   First album
12:00 - 17:59   Second album
18:00 - 23:59   Third album
```

The time slots are not meant to create artificial mystery.
They are simply a way to slow the site down.

You do not have to take in everything at once.
There are three moments in the day to pause, listen, save, or ignore.

## 🗂 What you will find

The site includes:

- **Today’s albums** — three recommendations unlocked throughout the day.
- **Album details** — artist, title, cover image, and related metadata.
- **Archive** — previous daily recommendations.
- **Detail pages** — individual pages for albums that have appeared before.

Once the final domains are ready, the project will live as an independent daily music site.

## ⚙️ How it works behind the scenes

Triangulum Daily 3 Albums is generated automatically.

Each morning, a generator collects and filters music data, selects the day’s albums, writes the site data, and publishes everything as static files. The public site does not depend on a live backend service while visitors are browsing.

In short:

```text
music data → daily selection → static site → daily listening
```

This keeps the project lightweight, stable, and suitable for long-term publishing.

## 🌐 Publishing plan

The project is intended to be published on my own domains and made accessible to listeners in and outside China.

This repository contains the system behind the site: the generator, publishing flow, front-end interface, and maintenance records. It is not primarily meant to be a general-purpose open-source template or something everyone is expected to clone and run locally.

The focus is the site itself:
three albums a day, appearing steadily, building an archive over time.

## 📌 Current status

Triangulum Daily 3 Albums is still being refined.

Current priorities include:

- Keeping the daily generation and publishing flow stable.
- Improving album selection and cover fallback behavior.
- Making the archive easier to browse.
- Preparing the site for custom domain publishing.
- Letting it grow into a small, long-running music place on the web.

------

Made for slower listening.
One day, three albums.
