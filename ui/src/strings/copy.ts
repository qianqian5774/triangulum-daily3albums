export type Language = "en" | "zh";

export const copy = {
  system: {
    status: {
      operational: "OPERATIONAL",
      degraded: "DEGRADED",
      error: "SYSTEM FAILURE",
      offline: "OFFLINE",
      archiveMode: "ARCHIVE MODE",
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
    eyebrow: "Triangulum Daily",
    body:
      "Triangulum Daily publishes nine album recommendations every day: three albums in each of three release windows. It was built as a way to step outside familiar recommendation loops and surface less obvious albums worth hearing.",
    schedule: "The site unlocks three albums at 08:00, 12:30, and 16:00 Beijing time.",
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
    intro: "Nine albums daily, released in three signal windows outside the usual recommendation loop.",
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
      label: "Time Lab",
      active: "DEBUG",
      realTime: "REAL BJT",
      offline: "OFFLINE / 07:59",
      slot0800: "08:00",
      slot1230: "12:30",
      slot1600: "16:00",
      transition2000: "20:00 transition",
      clear: "Clear debug time"
    },
    offline: {
      title: "SYSTEM OFFLINE",
      nextBoot: "NEXT BOOT 08:00",
      viewArchive: "View Archive",
      archiveViaHud: "Archive remains available from the HUD.",
      archivedLabel: "ARCHIVED",
      archivedHint: "Yesterday's intake (archived)",
      lockedHint: "Locked preview. Use the explicit Archive entry in the HUD.",
      lockedFeedback: "LOCKED / SIGNAL SEALED",
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
    intro: "Past Triangulum Daily entries. Pick a date to replay that day's output.",
    recentTitle: "Recent archive",
    recentIntro: "The latest seven static archive days, served from GitHub Pages JSON when available.",
    partialHint: "Fewer than seven archive days are currently available.",
    noRecent: "No archive days are available yet.",
    offlineMode: "ARCHIVE MODE / reading saved static signals",
    dayLabel: "Archive day",
    slotLabel: "Window",
    loadingDay: "Loading archived day...",
    missingDay: "Archive day unavailable",
    datesLabel: "Dates",
    loadingIndex: "Loading archive index...",
    empty: "Select a date to view archived albums.",
    openToday: "Back to Today"
  },
  share: {
    button: "Share Card",
    eyebrow: "Unlocked signal sheet",
    title: "Share Card",
    description: "Render a downloadable card from the albums already unlocked today.",
    version: "Version",
    theme: "Theme",
    language: "Language",
    day: "Day",
    night: "Night",
    locked: "This share card version is not unlocked yet.",
    download: "Download PNG",
    exporting: "Rendering...",
    close: "Close"
  },
  treatment: {
    dose: {
      readminister: "Re-administer Dose"
    },
    viewer: {
      eyebrow: "Album detail",
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
    slotInfoButton: "Explain recommendation role",
    slotInfo: {
      Headliner: "The most direct and immediately striking entry point for this signal window.",
      Lineage: "A recommendation tied to style lineage, historical influence, or a neighboring scene.",
      DeepCut: "A more hidden, exploratory recommendation for deeper listening."
    },
    metadata: {
      rating: "MusicBrainz Rating",
      tags: "MusicBrainz Tags",
      missing: "Pending"
    },
    overview: {
      title: "Overview",
      empty: "No Overview available.",
      continue: "Continue reading at Wikipedia...",
      licensePrefix: "Wikipedia content provided under the terms of the",
      licenseName: "Creative Commons BY-SA license"
    },
    cover: {
      missing: "No Cover",
      unknownArtist: "Unknown Artist"
    },
    links: {
      musicbrainz: "MusicBrainz",
      youtube: "YouTube"
    }
  },
  recordShop: {
    controls: {
      aria: "Record Shop display and sound controls",
      soundOn: "SOUND ON",
      soundOff: "SOUND OFF",
      enableSound: "Enable ambient sound and interface cues",
      disableSound: "Mute ambient sound and interface cues"
    },
    exterior: {
      aria: "Triangulum Daily Entry Diorama",
      fallbackAlt: "Triangulum Daily miniature record shop",
      approvedView: "ENTRY DIORAMA · PRESET",
      views: "VIEWS",
      orbitHint: "DRAG TO ORBIT · SCROLL TO SCALE",
      viewsAria: "Approved exterior camera views",
      viewNames: {
        axonometric: "AXONOMETRIC",
        front: "FRONT ELEVATION",
        right: "RIGHT ELEVATION",
        rear: "REAR ELEVATION",
        left: "LEFT ELEVATION",
        roof: "ROOF PLAN"
      },
      viewShort: {
        axonometric: "AXON",
        front: "FRONT",
        right: "RIGHT",
        rear: "REAR",
        left: "LEFT",
        roof: "ROOF"
      },
      zoomAria: "Scale the physical model",
      zoomOut: "Zoom out exterior model",
      zoomIn: "Zoom in exterior model",
      zoomReset: "Reset model zoom",
      reset: "RESET",
      doorAria: "Open the physical entrance door to enter the Public Record Gallery",
      enterHint: "CLICK THE DOOR TO ENTER",
      selectEntryViewHint: "SELECT FRONT OR AXON TO ENTER",
      projectInfo: "PROJECT INFO",
      dailyRhythm: "DAILY RHYTHM",
      infoAria: "Entry information",
      todayClosed: "TODAY · CLOSED / NEXT 08:00 BJT",
      recordsAvailable: "RECORDS AVAILABLE",
      doorOpen: "DOOR OPEN",
      crossing: "CROSSING THE THRESHOLD"
    },
    info: {
      closeAria: "Close information",
      close: "CLOSE ×",
      projectTitle: "TRIANGULUM DAILY",
      projectBody: "Triangulum Daily is a daily album recommendation experience that opens gradually across three Beijing Time windows.",
      projectSchedule: "Each window adds three complete albums to the same limited daily collection.",
      recordIncrement: "+3 records",
      finalIncrement: "+3 records · 9 total",
      projectNote: "The Entry Diorama establishes the shop; the Daily Device carries today's recommendation experience.",
      hoursTitle: "OPENING HOURS / BJT",
      closed: "CLOSED",
      threeRecords: "3 RECORDS",
      sixRecords: "6 RECORDS",
      nineRecords: "9 RECORDS",
      bjtNote: "BJT / BEIJING TIME"
    },
    interior: {
      environmentAlt: "Public Record Gallery interior",
      hudAria: "Gallery status HUD",
      date: "DATE",
      device: "DEVICE",
      bjt: "BJT",
      current: "CURRENT",
      history: "HISTORY",
      recentDates: "Recent dates",
      offline: "OFFLINE",
      ready: "READY",
      on: "ON",
      noWindow: "NO ACTIVE WINDOW / NEXT ONLINE 08:00 BJT",
      windows: "WINDOWS",
      records: "RECORDS AVAILABLE",
      dailyDevice: "DAILY DEVICE",
      windowReady: "WINDOW READY",
      openToday: "OPEN TODAY",
      arranging: "ARRANGING",
      triggerComplete: "TRIGGER COMPLETE",
      inventoryOpen: "INVENTORY OPEN",
      nextOnline: "NEXT ONLINE 08:00 BJT",
      recordsWaiting: "RECORDS WAITING",
      open: "OPEN",
      play: "PLAY",
      skip: "SKIP",
      continue: "CONTINUE",
      viewRecords: "VIEW RECORDS",
      shuffleAria: "Arranging today's records",
      interiorLabel: "INTERIOR",
      closePanel: "CLOSE ×",
      closePanelAria: "Close Daily Device",
      deviceReady: "DEVICE READY",
      secondAction: "Your records are arranged. Continue to browse.",
      todayInventoryAria: "Today record inventory",
      historyInventoryAria: "Historical record inventory",
      currentInventory: "CURRENT INVENTORY",
      historyInventory: "HISTORY INVENTORY",
      browseHint: "DRAG / ARROWS / SELECT A SPINE",
      previousRecord: "Previous record",
      nextRecord: "Next record",
      openRecord: "Open",
      returnExterior: "RETURN TO ENTRY",
      returnToday: "RETURN TO TODAY",
      treatmentCloseAria: "Close Treatment Viewer",
      overview: "OVERVIEW",
      selectionNote: "DAILY NOTE",
      metadataUnavailable: "No published overview is available for this release.",
      rating: "RATING",
      votes: "VOTES",
      publishedIssue: "PUBLISHED STATIC ISSUE",
      backToSpines: "BACK TO SPINES",
      roleLabels: {
        Headliner: "HEADLINER",
        Lineage: "LINEAGE",
        DeepCut: "DEEP CUT"
      }
    },
    loading: {
      title: "PUBLIC RECORD GALLERY",
      preparing: "PREPARING THE DAILY DEVICE",
      failed: "Daily issue failed to load"
    },
    debug: {
      aria: "Time debug controls",
      toggle: "TIME DEBUG",
      simulated: "SIMULATED",
      realClock: "REAL CLOCK",
      realTime: "REAL TIME",
      preset0759: "07:59 · OFFLINE",
      preset0800: "08:00 · DAY · 3",
      preset1230: "12:30 · DAY · 6",
      preset1600: "16:00 · DAY · 9",
      preset2100: "21:00 · NIGHT · 9",
      entryAria: "Entry transition debug",
      entryLabel: "ENTRY / DOOR",
      runEntry: "RUN ENTRY",
      resetEntry: "RESET ENTRY"
    }
  }
} as const;

const zhCopy = {
  system: {
    status: {
      operational: "运行正常",
      degraded: "降级运行",
      error: "系统错误",
      offline: "系统离线",
      archiveMode: "历史模式",
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
    eyebrow: "Triangulum Daily",
    body:
      "Triangulum Daily 每天发布九张专辑推荐：三个时段，每个时段三张。它最初是为了帮我跳出熟悉的推荐循环，看到一些不那么明显、但值得一听的专辑。",
    schedule: "站点按北京时间 08:00、12:30、16:00 三个时段发布，每个时段解锁三张专辑。",
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
    intro: "每日九张专辑，分三轮信号窗口释放，避开惯常推荐回路。",
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
      label: "时间实验室",
      active: "调试",
      realTime: "真实北京时间",
      offline: "离线 / 07:59",
      slot0800: "08:00",
      slot1230: "12:30",
      slot1600: "16:00",
      transition2000: "20:00 过渡",
      clear: "清除调试时间"
    },
    offline: {
      title: "系统离线",
      nextBoot: "下次启动 08:00",
      viewArchive: "查看历史",
      archiveViaHud: "历史入口保留在顶部 HUD。",
      archivedLabel: "历史",
      archivedHint: "昨日推荐归档",
      lockedHint: "锁定预览。请使用顶部 HUD 的明确历史入口。",
      lockedFeedback: "已锁定 / 信号封存",
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
    intro: "过去的 Triangulum Daily 记录。选择日期查看当天推荐。",
    recentTitle: "最近历史",
    recentIntro: "最近七个静态归档日期；可用数据少于七天时显示实际数量。",
    partialHint: "当前可用的历史日期少于七天。",
    noRecent: "暂无可用历史日期。",
    offlineMode: "历史模式 / 正在读取已保存的静态信号",
    dayLabel: "历史日期",
    slotLabel: "时段",
    loadingDay: "正在加载该日历史...",
    missingDay: "该日历史暂不可用",
    datesLabel: "日期",
    loadingIndex: "正在加载历史索引...",
    empty: "选择一个日期查看历史专辑。",
    openToday: "回到今日"
  },
  share: {
    button: "分享卡",
    eyebrow: "已解锁信号单",
    title: "分享卡",
    description: "根据今天已经解锁的专辑生成可下载卡片。",
    version: "版本",
    theme: "主题",
    language: "语言",
    day: "白昼",
    night: "夜间",
    locked: "这个分享卡版本尚未解锁。",
    download: "下载 PNG",
    exporting: "正在渲染...",
    close: "关闭"
  },
  treatment: {
    dose: {
      readminister: "重新查看"
    },
    viewer: {
      eyebrow: "专辑详情",
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
    slotInfoButton: "说明推荐角色",
    slotInfo: {
      Headliner: "当天该时段最直接、最醒目的入口推荐。",
      Lineage: "与风格脉络、历史影响或相邻场景有关的推荐。",
      DeepCut: "更隐蔽、更偏探索向的推荐。"
    },
    metadata: {
      rating: "MusicBrainz Rating",
      tags: "MusicBrainz Tags",
      missing: "暂无"
    },
    overview: {
      title: "Overview",
      empty: "暂无 Overview",
      continue: "Continue reading at Wikipedia...",
      licensePrefix: "Wikipedia content provided under the terms of the",
      licenseName: "Creative Commons BY-SA license"
    },
    cover: {
      missing: "无封面",
      unknownArtist: "未知艺人"
    },
    links: {
      musicbrainz: "MusicBrainz",
      youtube: "YouTube"
    }
  },
  recordShop: {
    controls: {
      aria: "唱片店显示与声音控制",
      soundOn: "声音 开",
      soundOff: "声音 关",
      enableSound: "开启环境声与界面音效",
      disableSound: "静音环境声与界面音效"
    },
    exterior: {
      aria: "Triangulum Daily 入口微缩模型",
      fallbackAlt: "Triangulum Daily 微缩唱片店",
      approvedView: "入口微缩模型 · 快速视角",
      views: "视角",
      orbitHint: "拖动自由旋转 · 滚轮缩放",
      viewsAria: "店外固定相机视角",
      viewNames: {
        axonometric: "轴测视角",
        front: "正立面",
        right: "右立面",
        rear: "后立面",
        left: "左立面",
        roof: "屋顶平面"
      },
      viewShort: {
        axonometric: "轴测",
        front: "正面",
        right: "右侧",
        rear: "背面",
        left: "左侧",
        roof: "屋顶"
      },
      zoomAria: "缩放实体模型",
      zoomOut: "缩小店外模型",
      zoomIn: "放大店外模型",
      zoomReset: "重置模型缩放",
      reset: "重置",
      doorAria: "打开实体大门，进入唱片陈列室",
      enterHint: "点击大门进入店内",
      selectEntryViewHint: "切换到正面或轴测视角进入",
      projectInfo: "项目说明",
      dailyRhythm: "每日节奏",
      infoAria: "入口信息",
      todayClosed: "今日 · 闭店 / 下次开放 08:00 BJT",
      recordsAvailable: "张唱片已开放",
      doorOpen: "大门开启",
      crossing: "正在越过门槛"
    },
    info: {
      closeAria: "关闭信息",
      close: "关闭 ×",
      projectTitle: "TRIANGULUM DAILY",
      projectBody: "Triangulum Daily 是一套按北京时间三个时段逐步开放的每日专辑推荐体验。",
      projectSchedule: "每个时段向同一组有限的每日收藏中加入三张完整专辑。",
      recordIncrement: "+3 张唱片",
      finalIncrement: "+3 张唱片 · 共 9 张",
      projectNote: "入口微缩模型建立唱片店世界，Daily Device 承载当天的推荐体验。",
      hoursTitle: "开放时间 / BJT",
      closed: "闭店",
      threeRecords: "3 张唱片",
      sixRecords: "6 张唱片",
      nineRecords: "9 张唱片",
      bjtNote: "BJT / 北京时间"
    },
    interior: {
      environmentAlt: "唱片陈列室店内环境",
      hudAria: "店内状态吊牌",
      date: "日期",
      device: "设备",
      bjt: "北京时间",
      current: "当前",
      history: "历史",
      recentDates: "最近日期",
      offline: "离线",
      ready: "就绪",
      on: "运行中",
      noWindow: "当前无开放时段 / 下次上线 08:00 BJT",
      windows: "个时段",
      records: "张唱片已开放",
      dailyDevice: "DAILY DEVICE",
      windowReady: "本时段已就绪",
      openToday: "开启今日",
      arranging: "正在整理",
      triggerComplete: "启动完成",
      inventoryOpen: "唱片库存已开启",
      nextOnline: "下次上线 08:00 BJT",
      recordsWaiting: "张唱片待浏览",
      open: "开启",
      play: "播放",
      skip: "跳过",
      continue: "继续",
      viewRecords: "查看唱片",
      shuffleAria: "正在整理今日唱片",
      interiorLabel: "店内",
      closePanel: "关闭 ×",
      closePanelAria: "关闭 Daily Device",
      deviceReady: "设备已就绪",
      secondAction: "唱片已整理好，继续浏览吧。",
      todayInventoryAria: "今日唱片库存",
      historyInventoryAria: "历史唱片库存",
      currentInventory: "今日库存",
      historyInventory: "历史库存",
      browseHint: "拖动 / 方向键 / 选择唱片书脊",
      previousRecord: "上一张唱片",
      nextRecord: "下一张唱片",
      openRecord: "打开",
      returnExterior: "返回入口",
      returnToday: "返回今日",
      treatmentCloseAria: "关闭专辑阅读层",
      overview: "专辑简介",
      selectionNote: "当日说明",
      metadataUnavailable: "该专辑暂无已发布的简介。",
      rating: "评分",
      votes: "票",
      publishedIssue: "已发布静态期刊",
      backToSpines: "返回唱片书脊",
      roleLabels: {
        Headliner: "主推",
        Lineage: "脉络",
        DeepCut: "深挖"
      }
    },
    loading: {
      title: "唱片陈列室",
      preparing: "正在准备 DAILY DEVICE",
      failed: "当日专辑期刊加载失败"
    },
    debug: {
      aria: "时间调试控制",
      toggle: "时间调试",
      simulated: "模拟时间",
      realClock: "真实时钟",
      realTime: "真实时间",
      preset0759: "07:59 · 离线",
      preset0800: "08:00 · 白昼 · 3",
      preset1230: "12:30 · 白昼 · 6",
      preset1600: "16:00 · 白昼 · 9",
      preset2100: "21:00 · 夜间 · 9",
      entryAria: "进门转场调试",
      entryLabel: "入口 / 大门",
      runEntry: "运行进门",
      resetEntry: "重置进门"
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
export type RecordShopCopy = ReturnType<typeof getCopy>["recordShop"];
