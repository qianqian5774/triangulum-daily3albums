export type Language = "en" | "zh";

export const copy = {
  system: {
    status: {
      operational: "OPERATIONAL",
      degraded: "DEGRADED",
      error: "SYSTEM FAILURE",
      booting: "BOOTING",
      synthesizing: "Synthesizing compounds..."
    },
    errors: {
      todayLoad: "TODAY JSON load failed",
      archiveLoad: "ARCHIVE JSON load failed",
      bsodTitle: "Critical Data Fault",
      bsodBody: "System failure. Patient advised to remain calm while diagnostics rerun.",
      errorCode: "ERROR_CODE: 0xTRI-ARCHIVE"
    },
    marqueeFallback: ["Triangulum intake stable", "Awaiting signals", "Scan ready"]
  },
  nav: {
    today: "Today",
    archive: "Archive",
    about: "Project Info"
  },
  controls: {
    language: "Language",
    english: "EN",
    chinese: "中文",
    font: "Text size",
    fontDown: "A-",
    fontUp: "A+",
    fontReset: "Reset"
  },
  about: {
    title: "Project Info",
    eyebrow: "Daily 3 Albums",
    body:
      "Triangulum Daily 3 Albums publishes nine album recommendations every day: three albums in each of three release windows. It was built as a way to step outside familiar recommendation loops and surface less obvious albums worth hearing.",
    schedule: "The site unlocks three albums at 06:00, 12:00, and 18:00 Beijing time.",
    static:
      "The daily data is generated offline and published as static files. Visitor browsers do not call external music APIs at page view time.",
    archive: "Archive pages keep previous daily recommendations available for later browsing.",
    github: "Open GitHub repository",
    close: "Close"
  },
  hud: {
    labels: {
      bjt: "BJT",
      status: "Status",
      debug: "DEBUG TIME ACTIVE"
    },
    window: {
      booting: "CALIBRATING",
      offline: "SYSTEM OFFLINE",
      label: "WINDOW"
    },
    clock: {
      nextCycle: "Next cycle",
      tMinus: "T-"
    },
    nextUnlock: "NEXT UNLOCK",
    nextBoot: "NEXT BOOT",
    countdownPrefix: "T-"
  },
  today: {
    label: "Today",
    headerFallback: "Calibrating today's triage",
    intro: "Three albums, released through the day outside the usual recommendation loop.",
    loading: "Synthesizing compounds...",
    themePrefix: "Theme",
    archiveCta: "Archive",
    timeline: {
      title: "Today Timeline",
      thumb: "Slot",
      nowLabel: "Now",
      locked: "Locked"
    },
    nowAvailable: "NOW AVAILABLE",
    returnToNow: "Return to now",
    ambientEnter: "Enter Ambient",
    ambientExit: "Exit ambient",
    debug: {
      label: "Debug time controls",
      minusMinute: "-1 minute",
      minusHour: "-1 hour",
      minusDay: "-1 day",
      addMinute: "+1 minute",
      addHour: "+1 hour",
      addDay: "+1 day",
      clear: "Clear debug time"
    },
    offline: {
      title: "SYSTEM OFFLINE",
      nextBoot: "NEXT BOOT 06:00",
      viewArchive: "View Archive",
      archivedLabel: "ARCHIVED",
      archivedHint: "Yesterday's intake (archived)",
      signalLost: "SIGNAL LOST",
      establishing: "ESTABLISHING LINK...",
      linkRestored: "LINK RESTORED",
      retry: "Retry now",
      noSignal: "NO SIGNAL / STATIC"
    }
  },
  archive: {
    label: "Archive",
    selectDate: "Select a date",
    intro: "Past Daily 3 Albums entries. Pick a date to replay that day's output.",
    datesLabel: "Dates",
    loadingIndex: "Loading archive index...",
    empty: "Select a date to view archived albums.",
    openToday: "Back to Today"
  },
  treatment: {
    dose: {
      readminister: "Re-administer Dose"
    },
    viewer: {
      enter: "Open album detail",
      close: "Close viewer",
      prev: "Previous dose",
      next: "Next dose"
    },
    slot: {
      Headliner: "Headliner",
      Lineage: "Lineage",
      DeepCut: "Deep Cut"
    },
    cover: {
      missing: "No Cover",
      unknownArtist: "Unknown Artist"
    },
    links: {
      musicbrainz: "MusicBrainz",
      youtube: "YouTube"
    }
  }
} as const;

const zhCopy = {
  system: {
    status: {
      operational: "运行正常",
      degraded: "降级运行",
      error: "系统错误",
      booting: "启动中",
      synthesizing: "正在生成..."
    },
    errors: {
      todayLoad: "today.json 加载失败",
      archiveLoad: "归档数据加载失败",
      bsodTitle: "关键数据故障",
      bsodBody: "系统暂时无法读取必要数据，请稍后重试。",
      errorCode: "ERROR_CODE: 0xTRI-ARCHIVE"
    },
    marqueeFallback: ["Triangulum 运行稳定", "等待信号", "扫描就绪"]
  },
  nav: {
    today: "今日",
    archive: "历史",
    about: "项目说明"
  },
  controls: {
    language: "语言",
    english: "EN",
    chinese: "中文",
    font: "字号",
    fontDown: "A-",
    fontUp: "A+",
    fontReset: "重置"
  },
  about: {
    title: "项目说明",
    eyebrow: "Daily 3 Albums",
    body:
      "Triangulum Daily 3 Albums 每天发布九张专辑推荐：三个时段，每个时段三张。它最初是为了帮我跳出熟悉的推荐循环，看到一些不那么明显、但值得一听的专辑。",
    schedule: "站点按北京时间 06:00、12:00、18:00 三个时段发布，每个时段解锁三张专辑。",
    static: "每日数据离线生成并发布为静态文件。访客打开页面时不会调用外部音乐 API。",
    archive: "历史页面会保留过去每天的推荐，方便回看。",
    github: "打开 GitHub 仓库",
    close: "关闭"
  },
  hud: {
    labels: {
      bjt: "北京时间",
      status: "状态",
      debug: "调试时间已启用"
    },
    window: {
      booting: "校准中",
      offline: "系统离线",
      label: "时段"
    },
    clock: {
      nextCycle: "下一轮",
      tMinus: "T-"
    },
    nextUnlock: "下次解锁",
    nextBoot: "下次启动",
    countdownPrefix: "T-"
  },
  today: {
    label: "今日",
    headerFallback: "正在校准今日推荐",
    intro: "每天三张专辑，按时段释放，尽量跳出惯常推荐循环。",
    loading: "正在生成...",
    themePrefix: "主题",
    archiveCta: "历史",
    timeline: {
      title: "今日时间线",
      thumb: "时段",
      nowLabel: "当前",
      locked: "未解锁"
    },
    nowAvailable: "当前内容已开放",
    returnToNow: "回到当前",
    ambientEnter: "进入沉浸",
    ambientExit: "退出沉浸",
    debug: {
      label: "调试时间控制",
      minusMinute: "-1 分钟",
      minusHour: "-1 小时",
      minusDay: "-1 天",
      addMinute: "+1 分钟",
      addHour: "+1 小时",
      addDay: "+1 天",
      clear: "清除调试时间"
    },
    offline: {
      title: "系统离线",
      nextBoot: "下次启动 06:00",
      viewArchive: "查看历史",
      archivedLabel: "历史",
      archivedHint: "昨日推荐归档",
      signalLost: "信号丢失",
      establishing: "正在建立连接...",
      linkRestored: "连接已恢复",
      retry: "立即重试",
      noSignal: "无信号 / 静态"
    }
  },
  archive: {
    label: "历史",
    selectDate: "选择日期",
    intro: "过去的 Daily 3 Albums 记录。选择日期查看当天推荐。",
    datesLabel: "日期",
    loadingIndex: "正在加载历史索引...",
    empty: "选择一个日期查看历史专辑。",
    openToday: "回到今日"
  },
  treatment: {
    dose: {
      readminister: "重新查看"
    },
    viewer: {
      enter: "打开专辑详情",
      close: "关闭浏览器",
      prev: "上一张",
      next: "下一张"
    },
    slot: {
      Headliner: "Headliner",
      Lineage: "Lineage",
      DeepCut: "Deep Cut"
    },
    cover: {
      missing: "无封面",
      unknownArtist: "未知艺人"
    },
    links: {
      musicbrainz: "MusicBrainz",
      youtube: "YouTube"
    }
  }
} as const;

export const localizedCopy = {
  en: copy,
  zh: zhCopy
} as const;

export function getCopy(language: Language = "en") {
  return localizedCopy[language] ?? copy;
}

export type CopySchema = typeof copy;
