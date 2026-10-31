// ILMA Web Frontend Logic (27 Oct 2026)
// Provides clean S-01 Home, S-02 Listening, Bank Services, Bank Detail (Report Card & 7 Checks), News

const T = {
  bn: {
    langBtn: "EN",
    wordmarkSub: "ILMA",
    tagline: "আপনার সঞ্চয়ের বিশ্বস্ত সাথী",
    homeIdle: "কথা বলতে যেকোনো জায়গায় ট্যাপ করুন",
    homeIdle2: "Tap anywhere to speak",
    listeningText: "শুনছি…",
    listeningPrompt: "ব্যাংকের নাম বা প্রশ্ন বলুন। থামিয়ে খুঁজতে দুইবার ট্যাপ করুন।",
    checkingText: "ইলমা ভাবছেন…",
    tryExamples: [
      "যেমন বলুন: “ইস্টার্ন ব্যাংক কেমন আছে?”",
      "যেমন বলুন: “ডাচ-বাংলা ব্যাংকের খেলাপি ঋণ কত?”",
      "যেমন বলুন: “আমার টাকা কি বীমা করা আছে?”",
      "যেমন বলুন: “ব্র্যাক ব্যাংকের ক্রেডিট রেটিং কী?”"
    ],
    tabs: {
      home: "হোম",
      services: "ব্যাংক সেবা",
      detail: "ব্যাংক",
      news: "খবর"
    },
    services: {
      title: "ব্যাংক সেবা ও সঞ্চয় সুরক্ষা",
      subtitle: "আমানত বীমা আইন ২০২৬ ও প্রকৃত মুনাফা নির্দেশিকা",
      listenBtn: "নিয়ম পড়ে শুনুন",
      insHeading: "আমানত সুরক্ষা হিসাব (Insurance Explainer)",
      insDesc: "“Tk 2 lakh of your Tk 5 lakh is covered” — কোনো অ্যাকাউন্ট বা ব্যক্তিগত তথ্য ছাড়াই হিসাব করুন।",
      amtLabel: "উদাহরণের পরিমাণ (BDT):",
      typeLabel: "প্রতিষ্ঠানের ধরন:",
      optBank: "বাণিজ্যিক ব্যাংক (আইন ২০২৬ প্রযোজ্য)",
      optNbfi: "আর্থিক প্রতিষ্ঠান - NBFI (বীমা কার্যকর ১ জুলাই ২০২৮)",
      insuredPart: "বীমা দ্বারা ১০০% সুরক্ষিত: ",
      uninsuredPart: "বীমাহীন সাধারণ দাবি: ",
      payoutNote: "আমানত সুরক্ষা আইন ২০২৬ অনুযায়ী বাংলাদেশ ব্যাংক ট্রাস্ট তহবিল ১৭ কর্মদিবসের মধ্যে এই অর্থ প্রদান করবে।",
      nbfiNote: "আর্থিক প্রতিষ্ঠানের (NBFI) আমানত বর্তমানে বীমা সুবিধার আওতাভুক্ত নয়। ১ জুলাই ২০২৮ থেকে কার্যকর হবে।",
      retHeading: "এফডিআর ও প্রকৃত মুনাফা ক্যালকুলেটর (Real Return)",
      retDesc: "উৎস কর (AIT) ও বর্তমান মুদ্রাস্ফীতি (৯.৮%) সমন্বয়ের পর আপনার কত টাকা লাভ থাকবে?",
      retAmtLabel: "উদাহরণ — আমানত/এফডিআর (টাকা):",
      retRateLabel: "বার্ষিক মুনাফার হার (%):",
      retTenorLabel: "মেয়াদ:",
      tinLabel: "টিআইএন (TIN) সার্টিফিকেট আছে (১০% কর, না থাকলে ১৫%)",
      grossProfit: "মোট মুনাফা: ",
      taxDeducted: "উৎস কর (AIT): ",
      netProfit: "কর-পরবর্তী মুনাফা: ",
      realReturn: "প্রকৃত লাভ (মুদ্রাস্ফীতি ৯.৮% সমন্বয়): "
    },
    detail: {
      whyHeading: "কেন এই অবস্থা? (৩টি প্রধান কারণ)",
      checksHeading: "৭টি মূল স্বাস্থ্য পরীক্ষা (7 Health Checks)",
      listenReport: "রিপোর্ট শুনুন",
      watchReport: "নজরে রাখুন",
      sourceBtn: "সূত্র ›",
      disclaimer: "এটি তথ্য, পরামর্শ নয়। টাকা রাখার আগে ব্যাংকে হার ও নিয়ম নিশ্চিত হয়ে নিন।"
    },
    news: {
      title: "ব্যাংকিং সংবাদ ও নোটিশ",
      subtitle: "প্রকাশিত খবর — প্রতিটি শিরোনামের সূত্র দেখুন",
      listenNews: "সংবাদ শুনুন"
    }
  },
  en: {
    langBtn: "BN",
    wordmarkSub: "ILMA",
    tagline: "Your savings partner",
    homeIdle: "Tap anywhere to speak",
    homeIdle2: "You can also speak Bangla",
    listeningText: "Listening…",
    listeningPrompt: "Say a bank name or ask a question. Double-tap to stop and search.",
    checkingText: "Ilma is thinking…",
    tryExamples: [
      "Try: “How is Eastern Bank doing?”",
      "Try: “What is Dutch-Bangla Bank's bad loan ratio?”",
      "Try: “Is my money insured?”",
      "Try: “What is BRAC Bank's credit rating?”"
    ],
    tabs: {
      home: "Home",
      services: "Services",
      detail: "Banks",
      news: "News"
    },
    services: {
      title: "Bank Services & Savings Protection",
      subtitle: "Deposit Protection Act 2026 & Real Return Guide",
      listenBtn: "Listen to guide",
      insHeading: "Deposit Insurance Breakdown",
      insDesc: "“Tk 2 lakh of your Tk 5 lakh is covered” — calculate without account or personal details.",
      amtLabel: "Example amount (BDT):",
      typeLabel: "Institution Type:",
      optBank: "Commercial Bank (Act 2026 applicable)",
      optNbfi: "NBFI - Financial Institution (Coverage starts 1 July 2028)",
      insuredPart: "100% Insured portion: ",
      uninsuredPart: "Uninsured general claim: ",
      payoutNote: "Under Deposit Protection Act 2026, Bangladesh Bank Trust Fund pays within 17 working days.",
      nbfiNote: "NBFI deposits are currently not insured; coverage begins 1 July 2028.",
      retHeading: "FDR & Real Return Calculator",
      retDesc: "What purchasing power remains after withholding tax (AIT) and 9.8% inflation?",
      retAmtLabel: "Example — deposit / FDR (BDT):",
      retRateLabel: "Annual Interest / Profit Rate (%):",
      retTenorLabel: "Tenor:",
      tinLabel: "Has TIN certificate (10% tax, otherwise 15%)",
      grossProfit: "Gross Profit: ",
      taxDeducted: "Withholding Tax (AIT): ",
      netProfit: "Net Profit: ",
      realReturn: "Real Return (Adjusted for 9.8% inflation): "
    },
    detail: {
      whyHeading: "Why this status? (Top 3 reasons)",
      checksHeading: "7 Key Health Checks",
      listenReport: "Listen in Bangla",
      watchReport: "Watch Bank",
      sourceBtn: "Source ›",
      disclaimer: "This is factual information, not financial advice. Verify terms directly with the bank."
    },
    news: {
      title: "Banking News & Notices",
      subtitle: "Published news — open each headline’s source",
      listenNews: "Listen to news"
    }
  }
};

const defaultSettings = { language: "bn", motion: true, swipe: true, speak: true, slow: false, micExplained: false, voiceonly: false, screenreader: false, ivrFinished: false, ivrLanguageChosen: false };
let appSettings = { ...defaultSettings };
try {
  const saved = JSON.parse(window.localStorage?.getItem("ilma-settings") || "null");
  if (saved) {
    if (["en", "bn"].includes(saved.language)) appSettings.language = saved.language;
    if (typeof saved.motion === "boolean") appSettings.motion = saved.motion;
    for (const key of ["swipe", "speak", "slow", "micExplained", "voiceonly", "screenreader", "ivrFinished", "ivrLanguageChosen"]) if (typeof saved[key] === "boolean") appSettings[key] = saved[key];
  }
} catch { /* Preferences still work when storage is unavailable. */ }
let lastAgentChoice = "";
let agentConversation = null, agentPanel = null, agentPendingResult = null, bargeMonitor = null;
let voiceLanguageReturn = null, voiceLanguageOverride = null;
let ivr = null, ivrPendingResult = null, ivrAudioCancel = null, ivrCandidates = [], ivrCandidateIndex = 0;
let currentLang = appSettings.language;
let suppressHomeClick = false;
let swipeClickTimer = null;
let currentTab = "home";
let currentBankId = null;
let reportCardData = null;
let audioRecorder = null;
let voiceAbort = null;
let isListening = false;
let recognitionStarting = false;
let isSearching = false;
let voiceRequest = 0;
let exampleTimer = null;
let greetingIndex = 0;
let greetingAnimation = null;
let reportRequest = 0;
let modalOpener = null;
let voiceConfig = { silence_ms: 1500, no_speech_ms: 6000 };
let activeVoiceContext = { tab: "home", bank_id: null };
let voiceHistory = [];
let lastVoiceTranscript = "";
let voiceFailures = 0;
let playbackRequest = 0;
let fixedClips = {};
let fixedClipAvailability = "loading";
let suppressReadoutClick = false;
let anonymousDevice = "";
try {
  anonymousDevice = window.localStorage?.getItem("ilma-device-id") || window.crypto?.randomUUID?.() || "";
  if (anonymousDevice) window.localStorage?.setItem("ilma-device-id", anonymousDevice);
} catch {}

function playTone(freq = 600, duration = 0.08) {
  try {
    const audioCtx = window.IlmaAudioSession ? window.IlmaAudioSession.getContext() : new (window.AudioContext || window.webkitAudioContext)();
    audioCtx.resume?.().catch(()=>{});
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
    osc.onended = () => {osc.disconnect?.();gain.disconnect?.();if(!window.IlmaAudioSession)audioCtx.close();};
  } catch (e) {}
}

function toBnDigits(num) {
  const bn = "০১২৩৪৫৬৭৮৯.";
  return String(num).replace(/[0-9.]/g, c => bn["0123456789.".indexOf(c)] || c);
}

function formatTaka(val) {
  const formatted = Math.round(Number(val)).toLocaleString("en-IN");
  return currentLang === "bn" ? toBnDigits(formatted) : formatted;
}

async function requestReadout(kind, institutionId = null) {
  if (suppressReadoutClick) { suppressReadoutClick = false; return; }
  const player = document.getElementById("ilma-player");
  if (player.src && !player.paused) { stopAudio(); return; }
  stopAudio(); const request = playbackRequest;
  try {
    const response = await fetch("/v1/speech", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, institution_id: institutionId, language: currentLang }) });
    if (!response.ok) throw new Error("speech_unavailable");
    const result = await response.json(); playVoiceAudio(result.audio_url, request, true);
  } catch { document.getElementById("sr-announcer").textContent = currentLang === "bn" ? "পড়ে শোনানোর সেবা এখন চালু নেই।" : "Spoken playback is not available."; }
}

function switchTab(tabName, keepVoiceStream = false, restoringRoute = false) {
  if(currentTab!==tabName){
    if(window.IlmaCatalogCommon)++window.IlmaCatalogCommon.state.epoch;
    ++reportRequest;
  }
  window.IlmaNavigation?.visit(tabName==="detail"?(currentBankId?{screen:"report",bank:currentBankId}:{screen:"banks"}):{screen:tabName});
  if (agentConversation && currentTab !== tabName) resetAgentConversation();
  currentTab = tabName;
  document.querySelector(".scr").classList.toggle("home-open", tabName === "home");
  document.querySelector(".scr").classList.toggle("report-open", tabName === "detail");
  if (!keepVoiceStream) stopAudio();
  if (!keepVoiceStream) stopListening();

  document.querySelectorAll(".dock button.dock-item").forEach(btn => {
    const isTarget = btn.getAttribute("data-tab") === tabName;
    btn.classList.toggle("on", isTarget);
    btn.setAttribute("aria-current", isTarget ? "page" : "false");
  });

  document.querySelectorAll(".tab-content").forEach(el => {
    el.classList.remove("active");
  });

  const targetPanel = document.getElementById(`tab-${tabName}`);
  if (targetPanel) {
    targetPanel.classList.add("active");
    if (tabName === "home") fitGreetingLine();
    document.getElementById("main-content").scrollTop = 0;
    window.scrollTo(0, 0);
    const srAnnounce = document.getElementById("sr-announcer");
    if (srAnnounce) {
      srAnnounce.textContent = currentLang === "bn" ? `${T[currentLang].tabs[tabName]} ট্যাব খোলা হয়েছে` : `${T[currentLang].tabs[tabName]} opened`;
    }
  }

  if (tabName === "detail" && !restoringRoute) {
    if (window.IlmaCatalog) window.IlmaCatalog.enter(tabName);
    else loadReportCard(currentBankId);
  } else if (tabName === "services" && !restoringRoute) {
    window.IlmaCatalog?.enter(tabName);
  } else if (tabName === "news") {
    loadNews();
  }
}

function saveSettings() {
  try { window.localStorage?.setItem("ilma-settings", JSON.stringify(appSettings)); } catch {}
}

function setLanguage(language, announce = true) {
  if (!["bn", "en"].includes(language)) return;
  voiceLanguageReturn=null;voiceLanguageOverride=null;document.getElementById("voice-language-chip").hidden=true;
  if (agentConversation && language !== currentLang) resetAgentConversation();
  if (isListening || recognitionStarting || isSearching) stopListening();
  stopAudio();
  currentLang = language;
  appSettings.language = language;
  saveSettings();
  updateLocalizedText();
  startExampleCycle();
  if (currentTab === "detail" && reportCardData) renderReportCard();
  window.IlmaCatalog?.relocalize();
  if (announce) document.getElementById("sr-announcer").textContent = currentLang === "bn"
    ? "ভাষা বাংলা করা হয়েছে।" : "Language changed to English.";
}

function applyTurnLanguage(language) {
  if(!['bn','en'].includes(language))return;
  currentLang=language;appSettings.language=language;saveSettings();updateLocalizedText();
  if(currentTab==='detail'&&reportCardData)renderReportCard();
  window.IlmaCatalog?.relocalize();
}
function undoTurnLanguage() {
  if(!voiceLanguageReturn)return;
  const language=voiceLanguageReturn;voiceLanguageReturn=null;voiceLanguageOverride=language;
  applyTurnLanguage(language);document.getElementById('voice-language-chip').hidden=true;
  if(!isSearching&&agentConversation){
    agentConversation.language=language;voiceLanguageOverride=null;
    void sendAgentChoice('repeat');
  }
}

function toggleLanguage() {
  setLanguage(currentLang === "bn" ? "en" : "bn");
}

function updateSettingsText() {
  const bn = currentLang === "bn";
  document.getElementById("text-size-label").textContent = bn ? "লেখার আকার" : "Text size";
  document.getElementById("text-size-preview").textContent = bn ? "ইস্টার্ন ব্যাংক · বার্ষিক ফি ৩,০০০ টাকা" : "Eastern Bank · Annual fee BDT 3,000";
  document.querySelectorAll("[data-text-size]").forEach((button,i) => {
    button.textContent = (bn ? ["ছোট","মাঝারি","বড়","খুব বড়"] : ["Small","Medium","Large","Extra large"])[i];
    button.setAttribute("aria-pressed", String(Number(button.dataset.textSize) === parseInt(document.documentElement.style.getPropertyValue("--fs") || "14")));
  });
  const labels = {
    "settings-voiceonly-label": bn ? "শুধু কথায়" : "Voice only",
    "settings-screenreader-label": bn ? "স্ক্রিন রিডার ব্যবহার করছি" : "I use a screen reader",
    "settings-title": bn ? "সেটিংস" : "Settings",
    "settings-language-label": bn ? "অ্যাপের ভাষা" : "App language",
    "settings-motion-label": bn ? "অ্যানিমেশন দেখান" : "Show animations",
    "settings-speak-label": bn ? "উত্তর পড়ে শোনান" : "Speak answers",
    "settings-slow-label": bn ? "ধীরে পড়ুন" : "Read slowly",
    "settings-swipe-label": bn ? "বামে সোয়াইপ করে ভাষা বদলান" : "Swipe left to change language",
    "settings-help": bn ? "হোমে বামে সোয়াইপ করে ভাষা বদলান। স্ক্রিন রিডার ব্যবহার করলে ভাষার বোতাম বা এই তালিকা ব্যবহার করুন।" : "Swipe left on Home to switch language. With a screen reader, use the language button or this list."
  };
  Object.entries(labels).forEach(([id, text]) => document.getElementById(id).textContent = text);
  document.getElementById("settings-btn").setAttribute("aria-label", bn ? "সেটিংস" : "Settings");
  document.getElementById("settings-close").setAttribute("aria-label", bn ? "বন্ধ করুন" : "Close settings");
  document.getElementById("settings-language").value = currentLang;
  document.getElementById("settings-motion").checked = appSettings.motion;
  for (const key of ["swipe", "speak", "slow", "voiceonly", "screenreader"]) document.getElementById(`settings-${key}`).checked = appSettings[key];
  document.querySelector(".scr").classList.toggle("motion-disabled", !appSettings.motion);
  updateFixedClipStatus();
}

function setupLanguageSwipe(target) {
  let origin = null;
  function suppressGestureClick() {
    suppressHomeClick = true;
    clearTimeout(swipeClickTimer);
    swipeClickTimer = setTimeout(() => { suppressHomeClick = false; }, 600);
  }
  function begin(x, y, id) {
    clearTimeout(swipeClickTimer);
    suppressHomeClick = false;
    origin = { x, y, id, time: Date.now() };
  }
  function cancel() {
    if (origin) suppressGestureClick();
    origin = null;
  }
  function finish(x, y, id, event) {
    const start = origin;
    origin = null;
    if (!start || id !== start.id) return;
    const dx = x - start.x, dy = y - start.y;
    // A drag/scroll must never become a microphone click, even if not a left swipe.
    if (Math.hypot(dx, dy) >= 12) suppressGestureClick();
    if (!appSettings.swipe || isListening || currentTab !== "home") return;
    if (dx <= -56 && Math.abs(dx) > Math.abs(dy) * 1.5 && Date.now() - start.time < 1500) {
      suppressGestureClick();
      if (event.cancelable) event.preventDefault();
      toggleLanguage();
      if ("vibrate" in navigator) navigator.vibrate(30);
    }
  }
  if (window.PointerEvent) {
    target.addEventListener("pointerdown", event => {
      if (event.isPrimary === false || (event.pointerType === "mouse" && event.button !== 0)) {
        cancel();
        return;
      }
      begin(event.clientX, event.clientY, event.pointerId);
      // Keep receiving the release if the finger/mouse leaves the button.
      try { target.setPointerCapture(event.pointerId); } catch {}
    });
    target.addEventListener("pointerup", event => finish(event.clientX, event.clientY, event.pointerId, event));
    target.addEventListener("pointercancel", cancel);
    target.addEventListener("lostpointercapture", cancel);
  } else {
    // Older mobile webviews may send Touch Events without Pointer Events.
    target.addEventListener("touchstart", event => {
      if (event.touches.length !== 1) { cancel(); return; }
      const touch = event.touches[0];
      begin(touch.clientX, touch.clientY, touch.identifier);
    }, { passive: true });
    target.addEventListener("touchend", event => {
      if (event.touches.length) { cancel(); return; }
      const touch = Array.from(event.changedTouches).find(item => item.identifier === origin?.id);
      if (touch) finish(touch.clientX, touch.clientY, touch.identifier, event);
    }, { passive: false });
    target.addEventListener("touchcancel", cancel);
  }
}

function updateLocalizedText() {
  const t = T[currentLang];
  document.documentElement.lang = currentLang;
  const rotationTitle=document.getElementById('orientation-title'), rotationDescription=document.getElementById('orientation-description');
  if(rotationTitle)rotationTitle.textContent=currentLang==='bn'?'ফোনটি সোজা করে ধরুন':'Please hold your phone upright';
  if(rotationDescription)rotationDescription.textContent=currentLang==='bn'?'সোজা করে ধরলে আগের পাতায় ফিরে যাবেন।':'Turn upright to return to the same page.';
  const languageButton = document.getElementById("lang-btn");
  languageButton.textContent = t.langBtn;
  languageButton.setAttribute("aria-pressed", String(currentLang === "en"));
  languageButton.setAttribute("aria-label", currentLang === "bn" ? "ইংরেজি ভাষায় বদলান" : "Switch to Bangla");
  const brandTagline = document.getElementById("wm-tagline");
  if (brandTagline) {
    brandTagline.textContent = t.tagline;
    brandTagline.lang = currentLang;
  }
  updateSettingsText();
  syncConnectivity();
  if (currentTab === 'detail' && !window.IlmaCatalog) loadBankOptions();
  stopGreetingCycle();

  document.querySelector("[data-tab='home'] span").textContent = t.tabs.home;
  document.querySelector("[data-tab='services'] span").textContent = t.tabs.services;
  document.querySelector("[data-tab='detail'] span").textContent = t.tabs.detail;
  document.querySelector("[data-tab='news'] span").textContent = t.tabs.news;

  document.getElementById("srv-title").textContent = t.services.title;
  document.getElementById("srv-subtitle").textContent = t.services.subtitle;
  document.getElementById("lbl-listen-srv").textContent = t.services.listenBtn;
  document.getElementById("srv-ins-heading").textContent = t.services.insHeading;
  document.getElementById("srv-ins-desc").textContent = t.services.insDesc;
  document.getElementById("srv-amt-label").textContent = t.services.amtLabel;
  document.getElementById("srv-type-label").textContent = t.services.typeLabel;
  document.getElementById("opt-bank").textContent = t.services.optBank;
  document.getElementById("opt-nbfi").textContent = t.services.optNbfi;
  document.getElementById("srv-ret-heading").textContent = t.services.retHeading;
  document.getElementById("srv-ret-desc").textContent = t.services.retDesc;
  document.getElementById("srv-ret-amt-lbl").textContent = t.services.retAmtLabel;
  document.getElementById("srv-ret-rate-lbl").textContent = t.services.retRateLabel;
  document.getElementById("srv-ret-tenor-lbl").textContent = t.services.retTenorLabel;
  document.getElementById("lbl-tin").textContent = t.services.tinLabel;

  document.getElementById("card-why-heading").textContent = t.detail.whyHeading;
  for (const code of ["strong", "watch", "high"]) document.getElementById(`scale-label-${code}`).textContent = STATUS_WORDS[code][currentLang === "bn" ? 0 : 1];
  document.querySelectorAll(".pin-note").forEach(note => { note.textContent = currentLang === "bn" ? "পিন, ওটিপি বা অ্যাকাউন্ট নম্বর কখনো চাই না" : "We never ask for your PIN, OTP or account number"; note.lang = currentLang; });
  document.getElementById("card-checks-heading").textContent = t.detail.checksHeading;
  document.getElementById("lbl-listen-rpt").textContent = t.detail.listenReport;
  document.getElementById("lbl-watch-rpt").textContent = t.detail.watchReport;
  document.getElementById("card-disclaimer").textContent = t.detail.disclaimer;

  document.getElementById("news-title").textContent = t.news.title;
  document.getElementById("news-sub").textContent = t.news.subtitle;
  document.getElementById("lbl-listen-news").textContent = t.news.listenNews;

  document.querySelectorAll(".dock-item").forEach(btn => btn.setAttribute("aria-label", t.tabs[btn.dataset.tab]));
  document.getElementById("voice-type").textContent = currentLang === "bn" ? "⌨ লিখে খুঁজুন" : "⌨ Type to search";
  document.getElementById("voice-text-label").textContent = currentLang === "bn" ? "ব্যাংকের নাম বা প্রশ্ন লিখুন" : "Type a bank name or question";
  document.getElementById("voice-text-submit").textContent = currentLang === "bn" ? "খুঁজুন" : "Search";
  document.getElementById("voice-dialog-title").textContent = currentLang === "bn" ? "ভয়েস অনুসন্ধান" : "Voice search";
  document.getElementById("voice-dialog-close").setAttribute("aria-label", currentLang === "bn" ? "বন্ধ করুন" : "Close");
  document.getElementById("bank-voice-btn").textContent = currentLang === "bn" ? "প্রশ্ন বলুন" : "Ask by voice";
  const miniTitle = document.getElementById("mini-voice-title");
  if (miniTitle) miniTitle.textContent = currentLang === "bn" ? "প্রশ্ন বলুন" : "Ask by voice";
  const miniClose = document.getElementById("mini-voice-close");
  if (miniClose) miniClose.setAttribute("aria-label", currentLang === "bn" ? "বন্ধ করুন" : "Close");
  const miniPrompt = document.getElementById("mini-voice-prompt");
  if (miniPrompt && !isListening && !isSearching) miniPrompt.textContent = T[currentLang].listeningPrompt;
  document.getElementById("home-tap-target").setAttribute("aria-label", currentLang === "bn" ? "কথা বলুন। ব্যাংকের নাম বলুন।" : "Speak. Say a bank name.");
  document.getElementById("btn-stop-listening").textContent = currentLang === "bn" ? "থামুন" : "Stop";
  document.getElementById("btn-stop-listening").setAttribute("aria-label", currentLang === "bn" ? "থামুন" : "Stop");
  if (currentTab === "news") loadNews();
  calculateInsuranceSplit();
  calculateRealReturn();
}

// One bilingual line; never split Bengali conjuncts into individual characters.
const greetingFrames = [
  { lang: "bn", text: T.bn.homeIdle, example: false },
  { lang: "en", text: T.en.homeIdle, example: false },
  { lang: "bn", text: "ইস্টার্ন ব্যাংক কেমন আছে?", example: true },
  { lang: "en", text: "How is Eastern Bank doing?", example: true }
];

function fitGreetingLine() {
  const line = document.getElementById("home-greeting-line");
  if (!line || !line.getBoundingClientRect) return;
  // Use rem so browser font-size preferences are preserved. At enlarged text
  // sizes allow wrapping rather than shrinking below the 16px design minimum.
  line.style.whiteSpace = "nowrap";
  let size = 1.375;
  line.style.fontSize = `${size}rem`;
  while (line.scrollWidth > line.clientWidth + 1 && size > 1) {
    size = Math.max(1, size - 0.025);
    line.style.fontSize = `${size}rem`;
  }
  if (line.scrollWidth > line.clientWidth + 1) line.style.whiteSpace = "normal";
}

function showGreetingFrame(frame, animate = false) {
  const line = document.getElementById("home-greeting-line");
  if (!line) return;
  greetingAnimation?.cancel();
  line.textContent = frame.text;
  line.lang = frame.lang;
  line.classList.toggle("is-example", frame.example);
  fitGreetingLine();
  if (animate && !greetingMotionReduced() && line.animate) {
    try {
      greetingAnimation = line.animate([
      { opacity: 0, transform: "translateY(6px)", clipPath: "inset(0 100% 0 0)" },
      { opacity: 1, transform: "translateY(0)", clipPath: "inset(0 0% 0 0)" }
      ], { duration: 700, easing: "cubic-bezier(.22,1,.36,1)" });
    } catch {
      // Text rotation still works when the reveal animation is unsupported.
      greetingAnimation = null;
    }
  }
}

function greetingMotionReduced() {
  return !appSettings.motion || Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
}

function pauseGreetingCycle() {
  clearInterval(exampleTimer);
  exampleTimer = null;
  greetingAnimation?.cancel();
  greetingAnimation = null;
}

function stopGreetingCycle() {
  pauseGreetingCycle();
  showGreetingFrame({ lang: currentLang, text: T[currentLang].homeIdle, example: false });
}

function startExampleCycle() {
  if (ivr?.active || agentPanel?.active) return;
  document.getElementById("home-orb").setAttribute("data-reduced-motion", String(greetingMotionReduced()));
  pauseGreetingCycle();
  if (currentTab !== "home" || isListening || recognitionStarting || isSearching || document.hidden || document.getElementById("settings-dialog").open || document.getElementById("voice-feedback").open || document.getElementById("mini-voice-modal")?.open) return;
  const frames = greetingFrames.filter(frame => frame.lang === currentLang);
  greetingIndex = 0;
  showGreetingFrame(frames[0], true);
  exampleTimer = setInterval(() => {
    greetingIndex = (greetingIndex + 1) % frames.length;
    showGreetingFrame(frames[greetingIndex], true);
  }, 3800);
}

// S-02: Record locally, upload only to ILMA; Meta credentials stay on the server.
function setupSpeech() { /* Audio capture is initialized only after a user tap. */ }

function isMiniVoiceFlow() {
  return activeVoiceContext != null && (activeVoiceContext.tab === "services" || activeVoiceContext.tab === "bank");
}

function openMiniVoiceModal() {
  const dialog = document.getElementById("mini-voice-modal");
  if (!dialog) return;
  dialog.hidden = false;
  if (!dialog.open) {
    try { dialog.showModal(); } catch {}
  }
  pauseGreetingCycle();
}

function closeMiniVoiceModal() {
  const dialog = document.getElementById("mini-voice-modal");
  if (!dialog) return;
  dialog.hidden = true;
  if (dialog.open) {
    try { dialog.close(); } catch {}
  }
}

function setMiniVoiceState(text) {
  const state = document.getElementById("mini-voice-state");
  if (state && text != null) state.textContent = text;
}

function setWaveformState(state) {
  const wave = document.getElementById("home-orb");
  wave.setAttribute("data-state", state);
  const miniWave = document.getElementById("mini-voice-wave");
  if (miniWave) miniWave.setAttribute("data-state", state);
  wave.style.setProperty?.("--wave-level", "1");
  const button = document.getElementById("home-tap-target");
  button.setAttribute("aria-pressed", String(state === "listening"));
  button.setAttribute("aria-busy", String(state === "thinking" || state === "starting"));
  button.setAttribute("aria-label", state === "listening"
    ? (currentLang === "bn" ? "রেকর্ডিং চলছে। থামিয়ে খুঁজতে দুইবার ট্যাপ করুন অথবা থামুন বোতাম চাপুন।" : "Recording. Double-tap to stop and search, or use the Stop button.")
    : (currentLang === "bn" ? "কথা বলুন। ব্যাংকের নাম বলুন।" : "Speak. Say a bank name."));
}

function setVoiceState(text) {
  if (agentPanel?.active) document.getElementById("agent-state").textContent = text;
  document.getElementById("home-idle-view").hidden = true;
  document.getElementById("home-listening-view").hidden = false;
  document.getElementById("listening-state-text").textContent = text;
  setMiniVoiceState(text);
}

async function startListening(providedStream = null) {
  if (isListening || recognitionStarting || isSearching) {providedStream?.getTracks().forEach(t=>t.stop());return;}
  lastVoiceTranscript = "";
  document.getElementById("voice-transcript").hidden = true;
  stopAudio();
  if (navigator.onLine === false) { showVoiceFallback("offline"); return; }
  closeVoiceFeedback();
  if (!appSettings.micExplained) {
    // A permission explanation is waiting for the user, not a silent reply.
    if(agentPanel?.active)agentPanel.suspend();
    const bn = currentLang === "bn";
    document.getElementById("mic-permission-title").textContent = bn ? "কথা বলতে মাইক্রোফোন লাগবে" : "Use your microphone to speak";
    document.getElementById("mic-permission-copy").textContent = bn ? "আপনার কথা লিখে ব্যাংক খুঁজব। লেখা হওয়ার পর রেকর্ডিং মুছে ফেলা হয়। পিন বা অ্যাকাউন্ট নম্বর বলবেন না।" : "We transcribe your voice to find bank information, then delete the recording. Never say your PIN or account number.";
    document.getElementById("mic-permission-allow").textContent = bn ? "অনুমতি দিন" : "Continue to microphone permission";
    document.getElementById("mic-permission-later").textContent = bn ? "এখন না — লিখে খুঁজুন" : "Not now — type instead";
    pauseGreetingCycle();
    document.getElementById("mic-permission-dialog").showModal();
    return;
  }
  closeVoiceFeedback();
  if (!ivr?.active && isMiniVoiceFlow()) openMiniVoiceModal();
  document.getElementById("voice-matches").replaceChildren();
  document.getElementById("voice-answer-sources").replaceChildren();
  document.getElementById("voice-transcript").hidden = true;
  lastVoiceTranscript = "";
  if (window.isSecureContext === false) { showVoiceFallback("insecure"); return; }
  if (!window.IlmaVoiceRecorder?.supported()) { showVoiceFallback("unsupported"); return; }
  const request = ++voiceRequest;
  recognitionStarting = true;
  setWaveformState("starting");
  pauseGreetingCycle();
  setVoiceState(currentLang === "bn" ? "মাইক্রোফোন চালু হচ্ছে…" : "Starting microphone…");
  document.getElementById("listening-transcript").textContent = "";
  document.getElementById("listening-prompt").textContent = T[currentLang].listeningPrompt;
  const miniTranscriptStarting = document.getElementById("mini-voice-transcript");
  if (miniTranscriptStarting) miniTranscriptStarting.textContent = "";
  const miniPromptStarting = document.getElementById("mini-voice-prompt");
  if (miniPromptStarting) miniPromptStarting.textContent = T[currentLang].listeningPrompt;
  const recorder = new window.IlmaVoiceRecorder();
  audioRecorder = recorder;
  try {
    await recorder.start({
      stream: providedStream,
      silenceMs: voiceConfig.silence_ms,
      maxMs: 15000,
      noSpeechMs: currentTab==='home'||ivr?.active||agentPanel?.active ? 8000 : 6000,
      onLevel: level => {
        if (!greetingMotionReduced()) document.getElementById("home-orb").style.setProperty("--wave-level", String(1 + Math.min(.65, level * 8)));
      },
      onNoise: () => { document.getElementById("listening-prompt").textContent = currentLang === "bn" ? "চারপাশে শব্দ বেশি, একটু শান্ত জায়গায় বলুন" : "It is noisy. Try speaking somewhere quieter."; },
      onComplete: finishRecording,
      onError: code => {
        if (request !== voiceRequest) return;
        stopListening();
        showVoiceFallback(code);
      }
    });
    if (request !== voiceRequest) { recorder.cancel(); return; }
    recognitionStarting = false;
    isListening = true;
    if (ivr?.active && ivr.id === 'mic') {
      stopListening();
      return ivr.enter(appSettings.ivrLanguageChosen ? 'menu' : 'language');
    }
    if (ivr?.active) document.getElementById("ivr-status").textContent = T[currentLang].listeningPrompt;
    setWaveformState("listening");
    setVoiceState(T[currentLang].listeningText);
    document.getElementById("btn-stop-listening").textContent = currentLang === "bn" ? "থামুন ও খুঁজুন" : "Stop and search";
    document.getElementById("btn-stop-listening").setAttribute("aria-label", currentLang === "bn" ? "রেকর্ডিং থামিয়ে খুঁজুন" : "Stop recording and search");
    const miniStop = document.getElementById("mini-voice-stop");
    if (miniStop) miniStop.textContent = currentLang === "bn" ? "থামুন ও খুঁজুন" : "Stop and search";
    document.getElementById("sr-announcer").textContent = T[currentLang].listeningText;
    playTone(660, 0.08);
    if ("vibrate" in navigator) navigator.vibrate(30);
  } catch (error) {
    if (request !== voiceRequest) return;
    stopListening();
    showVoiceFallback(error.name === "NotAllowedError" ? "not-allowed" : error.name === "NotFoundError" ? "audio-capture" : "unavailable");
  }
}

async function finishRecording() {
  if (!isListening || !audioRecorder || isSearching) return;
  const recorder = audioRecorder, request = voiceRequest;
  isListening = false;
  isSearching = true;
  setWaveformState("thinking");
  setVoiceState(T[currentLang].checkingText);
  document.getElementById("btn-stop-listening").textContent = currentLang === "bn" ? "বাতিল করুন" : "Cancel";
  document.getElementById("btn-stop-listening").setAttribute("aria-label", currentLang === "bn" ? "বাতিল করুন" : "Cancel transcription");
  const miniStopCancel = document.getElementById("mini-voice-stop");
  if (miniStopCancel) miniStopCancel.textContent = currentLang === "bn" ? "বাতিল করুন" : "Cancel";
  try {
    let audio = await recorder.finish();
    playTone(440, .08);
    if ("vibrate" in navigator) navigator.vibrate(30);
    if (request !== voiceRequest) return;
    if (audioRecorder === recorder) audioRecorder = null;
    if (!audio.size) throw new Error('no_speech');
    audio.ilmaTruncated=Boolean(recorder.truncated);
    if (audio.size > 1024 * 1024) throw new Error("audio_too_large");
    await sendVoiceInput(audio, null, request);
    await flushIvrResult();

  } catch (error) {
    if (request !== voiceRequest) return;
    stopListening();
    showVoiceFallback(error.name === "AbortError" ? "voice_timeout" : error.message);
  }
}

function showVoiceFallback(code = "unmatched") {
  if (agentPanel?.active) {
    document.getElementById('agent-state').textContent = currentLang === 'bn' ? 'কথা শোনা যায়নি। একটি বিকল্প বেছে নিন বা আবার বলুন।' : 'Could not hear a reply. Choose an option or try speaking again.';
    agentPanel.captureFailed(['no_speech','no-speech'].includes(code)); return;
  }
  if (ivr?.active) {
    document.getElementById('ivr-status').textContent = ['no_speech','no-speech'].includes(code)
      ? (currentLang === 'bn' ? 'কথা শোনা যায়নি। এখন এক বা দুইবার চাপুন।' : 'No speech heard. Tap once or twice now.')
      : (currentLang === 'bn' ? 'ভয়েস পাওয়া যাচ্ছে না। এক বা দুইবার চাপুন, অথবা এড়িয়ে যান।' : 'Voice unavailable. Tap once or twice, or Skip.');
    if (!['no_speech','no-speech'].includes(code)) ivr.silenceRetries = 2;
    ivr.silent(); return;
  }

  closeMiniVoiceModal();
  if (code === "no_speech") code = "no-speech";
  document.getElementById("voice-answer-sources").replaceChildren();
  document.getElementById("voice-matches").replaceChildren();
  const bn = currentLang === "bn";
  voiceFailures++;
  const transcript = document.getElementById("voice-transcript");
  // Offline, nothing was recorded, so a "no transcript" line would only confuse.
  transcript.hidden = code === "offline" && !lastVoiceTranscript;
  transcript.textContent = lastVoiceTranscript
    ? (bn ? "আপনি বলেছেন: " : "You said: ") + `“${lastVoiceTranscript}”`
    : (bn ? "এই চেষ্টায় কোনো প্রতিলিপি পাওয়া যায়নি।" : "No transcript was received for this attempt.");
  const messages = {
    request_limited: bn ? "অনুরোধের সীমা হয়েছে। একটু পরে আবার চেষ্টা করুন।" : "The service request limit was reached. Please wait before trying again.",
    upload_timeout: bn ? "আপলোডে সময় বেশি লাগছে। সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।" : "The upload timed out. Check your connection and try again.",
    origin_denied: bn ? "অ্যাপের অনুমোদিত ঠিকানা থেকে খুলুন।" : "Open the app from its approved address.",
    offline: bn ? "কথা বলতে ইন্টারনেট লাগবে; আগে দেখা ব্যাংক অফলাইনে দেখা যাবে।" : "Voice needs the internet. Banks you viewed before are available offline.",
    unclear: bn ? "বুঝতে পারিনি। আবার বলুন বা লিখুন।" : "Not understood. Please speak again or type.",
    transcript_language_mismatch: bn ? "ভয়েস সেবা অন্য লিপিতে কথা লিখেছে। উপরের লেখা দেখুন, আবার বলুন বা লিখে সংশোধন করুন।" : "The speech service returned text in an unexpected script. Check the text above, then speak again or type a correction.",
    intent_unavailable: bn ? "প্রশ্নটি বুঝতে পারিনি। আবার বলুন বা লিখুন।" : "Could not understand the question. Speak again or type.",
    voice_dependency_missing: bn ? "ভয়েস সেবা প্রস্তুত নয়। লিখে খুঁজুন।" : "Voice service is not ready. Try typing.",
    bank_data_unavailable: bn ? "ব্যাংকের তথ্য এখন পাওয়া যাচ্ছে না। আবার চেষ্টা করুন।" : "Bank data is currently unavailable. Please try again.",
    voice_unconfigured: bn ? "ভয়েস সেবা এখনও চালু হয়নি।" : "Voice service is not configured yet.",
    voice_backend_outdated: bn ? "সার্ভারে ভয়েস অনুসন্ধান চালু নেই। অ্যাপের সার্ভার আপডেট করা প্রয়োজন।" : "Voice search is unavailable on this server. The app backend needs to be updated or restarted.",
    voice_incomplete_response: bn ? "উত্তর আসার আগেই সংযোগ শেষ হয়েছে। আবার চেষ্টা করুন।" : "The connection ended before the answer arrived. Please try again.",
    voice_internal_error: bn ? "অনুরোধটি শেষ করা যায়নি। আবার চেষ্টা করুন।" : "Could not finish this request. Please try again.",
    recording_finalize_timeout: bn ? "রেকর্ডিংটি শেষ করা যায়নি। আবার রেকর্ড করুন।" : "The recording could not finish. Please record again.",
    daily_limit: bn ? "আজকের প্রশ্নের সীমা শেষ। ব্যাংকের অবস্থা, বীমা ও হার দেখা যাবে।" : "Daily question limit reached. Bank status, insurance and rate lookups remain available.",
    invalid_request: bn ? "প্রশ্নটি পাঠানো যায়নি। আবার চেষ্টা করুন বা লিখুন।" : "The question could not be submitted. Please try again or type.",
    voice_timeout: bn ? "ভয়েস সেবায় সময় বেশি লাগছে। আবার চেষ্টা করুন।" : "Transcription timed out. Try again.",
    voice_rate_limited: bn ? "একটু পরে আবার চেষ্টা করুন।" : "Voice service is busy. Try again shortly.",
    voice_unavailable: bn ? "ভয়েস সেবায় সংযোগ করা যায়নি। আবার চেষ্টা করুন।" : "Could not transcribe the recording. Try again.",
    audio_too_large: bn ? "রেকর্ডিংটি খুব বড়। ছোট করে আবার বলুন।" : "Recording is too large. Try a shorter recording.",
    invalid_audio: bn ? "রেকর্ডিংটি পড়া যায়নি। আবার চেষ্টা করুন।" : "Could not read the recording. Try again.",
    unsupported: bn ? "এই ব্রাউজারে অডিও রেকর্ডিং চালু নেই। সমর্থিত ব্রাউজারে খুলুন।" : "Audio recording is unavailable in this browser. Open the app in a supported browser.",
    insecure: bn ? "মাইক্রোফোন ব্যবহার করতে অ্যাপটি HTTPS ঠিকানায় খুলুন।" : "Open the app over HTTPS to use the microphone.",
    "not-allowed": bn ? "মাইক্রোফোনের অনুমতি বন্ধ আছে। ব্রাউজারের সাইট সেটিংসে অনুমতি দিয়ে আবার চেষ্টা করুন।" : "Microphone access is blocked. Allow it in your browser’s site settings, then try again.",
    "audio-capture": bn ? "মাইক্রোফোন পাওয়া যায়নি। মাইক্রোফোন সংযোগ পরীক্ষা করুন।" : "No microphone is available. Check your microphone connection.",
    "no-speech": bn ? "কথা শোনা যায়নি। আবার ট্যাপ করে ব্যাংকের নাম বলুন।" : "No speech was heard. Tap again and say a bank name.",
    network: bn ? "ভয়েস সেবায় সংযোগ করা যায়নি। ইন্টারনেট পরীক্ষা করে আবার চেষ্টা করুন।" : "Could not reach the voice service. Check your internet connection and try again.",
    "service-not-allowed": bn ? "ব্রাউজার ভয়েস সেবা চালু করতে পারছে না। অন্য সমর্থিত ব্রাউজারে চেষ্টা করুন।" : "The browser cannot use its voice service. Try another supported browser.",
    "language-not-supported": bn ? "এই ব্রাউজারের ভয়েস সেবায় বাংলা সমর্থিত নয়।" : "The selected language is not supported by this browser’s voice service.",
    search: bn ? "ব্যাংকের তথ্য খোঁজা যায়নি। সংযোগ পরীক্ষা করে আবার চেষ্টা করুন।" : "Could not search bank information. Check the connection and try again.",
    unmatched: bn ? "ব্যাংকের নাম বোঝা যায়নি। আবার ট্যাপ করে শুধু ব্যাংকের নাম বলুন।" : "No matching bank was found. Tap again and say just the bank name.",
    multiple: bn ? "একাধিক ব্যাংকের নাম পাওয়া গেছে। নিচে একটি বেছে নিন।" : "More than one bank was found. Choose one below."
  };
  document.getElementById("voice-feedback-message").textContent = messages[code] || (bn ? "ভয়েস চালু করা যায়নি। আবার চেষ্টা করুন।" : "Could not start voice recognition. Try again.");
  openVoiceFeedback();
  document.getElementById("voice-retry").textContent = bn ? "আবার চেষ্টা করুন" : "Try again";
  if (voiceFailures >= 2 && ["no-speech", "audio-capture"].includes(code)) document.getElementById("voice-feedback-message").textContent += bn ? " চারপাশে শব্দ বেশি হলে লিখে খুঁজুন।" : "If it is noisy, try typing instead.";
  if (code === "transcript_language_mismatch") document.getElementById("voice-text-input").value = lastVoiceTranscript;
  if (voiceFailures >= 2 || ["not-allowed", "audio-capture", "unsupported", "transcript_language_mismatch"].includes(code)) showTyping();
  playFixedClip(code === "offline" ? "E-01" : ["not-allowed", "audio-capture"].includes(code) ? "E-03" : "E-04");
  startExampleCycle();
}

function stopListening() {
  setWaveformState("idle");
  voiceRequest++;
  audioRecorder?.cancel();
  audioRecorder = null;
  voiceAbort?.abort();
  voiceAbort = null;
  recognitionStarting = false;
  isSearching = false;
  if (isListening) {
    isListening = false;
    playTone(440, 0.08);
    if ("vibrate" in navigator) navigator.vibrate(30);
  }
  closeVoiceFeedback();
  closeMiniVoiceModal();
  const listeningView = document.getElementById("home-listening-view");
  if (listeningView) {
    listeningView.hidden = true;
    listeningView.classList.remove("active");
  }
  const idleView = document.getElementById("home-idle-view");
  if (idleView) {
    idleView.hidden = false;
  }
  startExampleCycle();
}

function openVoiceFeedback() {
  const dialog = document.getElementById("voice-feedback");
  dialog.hidden = false;
  if (!dialog.open) dialog.showModal();
  pauseGreetingCycle();
}

function closeVoiceFeedback() {
  const dialog = document.getElementById("voice-feedback");
  if (dialog.open) dialog.close();
  dialog.hidden = true;
}

function showTyping() {
  openVoiceFeedback();
  document.getElementById("voice-text-form").hidden = false;
  document.getElementById("voice-text-input").focus();
}

function stopAudio() {
  bargeMonitor?.cancel();bargeMonitor=null;
  const speechStop=document.getElementById("agent-stop-speech");if(speechStop)speechStop.hidden=true;
  if (ivrAudioCancel) { const cancel = ivrAudioCancel; ivrAudioCancel = null; cancel(); }
  setWaveformState(isListening ? "listening" : recognitionStarting ? "starting" : isSearching ? "thinking" : "idle");
  playbackRequest++;
  const player = document.getElementById("ilma-player");
  player.pause?.();
  player.removeAttribute?.("src");
  player.load?.();
  const labels = { "lbl-listen-rpt": T[currentLang].detail.listenReport, "lbl-listen-srv": T[currentLang].services.listenBtn, "lbl-listen-news": T[currentLang].news.listenNews };
  Object.entries(labels).forEach(([id, text]) => document.getElementById(id).textContent = text);
  const compareListen=document.getElementById('compare-listen');
  const accountListen=document.getElementById('account-listen');if(accountListen)accountListen.textContent=window.IlmaAccounts?.listenLabel?.()||(currentLang==='bn'?'এই হিসাব শুনুন':'Listen in Bangla');
  const depositListen=document.getElementById('deposit-listen');if(depositListen)depositListen.textContent=window.IlmaDeposits?.listenLabel?.()||(currentLang==='bn'?'এই সঞ্চয়ের হিসাব শুনুন':'Listen in Bangla');
  const loanListen=document.getElementById('loan-listen');if(loanListen)loanListen.textContent=window.IlmaLoans?.listenLabel?.()||'Listen';
  if(compareListen)compareListen.textContent=window.IlmaCatalog?.listenLabel?.()||(currentLang==='bn'?'শুনুন':'Listen');
}

function playVoiceAudio(url, request = playbackRequest, manual = false, onError = null) {
  if (request !== playbackRequest || (!manual && !appSettings.speak) || !(url?.startsWith("data:audio/mpeg;base64,") || (/^\/static\/audio\/fixed\/[a-zA-Z0-9_-]+\.(?:opus|mp3)$/.test(url || "") || (/^\/static\/audio\/services\/bn\/(?:card-|deposit_|loan_)[a-z0-9_-]+\.mp3\?v=[a-f0-9]{16}$/.test(url || "") || /^\/static\/audio\/(?:bank|loans|deposits|accounts)\/bn\/[a-z0-9_-]+\.mp3\?v=[a-f0-9]{16}$/.test(url || "")) || /^\/v1\/audio\/[A-Za-z0-9_-]{32}\.mp3$/.test(url || "")))) return false;
  const player = document.getElementById("ilma-player");
  player.src = url;
  player.playbackRate = appSettings.slow ? .85 : 1;
  const label = currentTab === "detail" ? "lbl-listen-rpt" : currentTab === "services" ? "lbl-listen-srv" : currentTab === "news" ? "lbl-listen-news" : null;
  if (label) document.getElementById(label).textContent = currentLang === "bn" ? "থামুন" : "Stop";
  const compareListen=document.getElementById('compare-listen');
  if(currentTab==='services'&&compareListen)compareListen.textContent=currentLang==='bn'?'থামুন':'Stop';
  const loanListen=document.getElementById('loan-listen');if(currentTab==='services'&&loanListen)loanListen.textContent=currentLang==='bn'?'থামুন':'Stop';
  const depositListen=document.getElementById('deposit-listen');if(currentTab==='services'&&depositListen)depositListen.textContent=currentLang==='bn'?'থামুন':'Stop';
  const accountListen=document.getElementById('account-listen');if(currentTab==='services'&&accountListen)accountListen.textContent=currentLang==='bn'?'থামুন':'Stop';
  player.play?.().catch(() => { if(request!==playbackRequest)return; stopAudio(); document.getElementById("sr-announcer").textContent = currentLang === "bn" ? "উত্তর শুনতে শুনুন বোতাম চাপুন।" : "Tap Listen to hear the answer."; onError?.(); });
  return true;
}

function updateFixedClipStatus() {
  const status = document.getElementById('settings-fixed-audio');
  if (!status) return;
  status.hidden = fixedClipAvailability !== 'unavailable';
  status.textContent = currentLang === 'bn'
    ? 'সংরক্ষিত নির্দেশনার অডিও এখন নেই। পর্দার লেখা ব্যবহার করুন। অনলাইন কণ্ঠসেবা আলাদাভাবে কাজ করতে পারে।'
    : 'Saved prompt audio is not available. Use the on-screen text. Online speech may still be available.';
}

async function loadFixedClips() {
  try {
    const response = await fetch('/v1/content/fixed', {cache: 'no-store'});
    if (!response.ok) throw Error('fixed_audio_unavailable');
    const content = await response.json();
    fixedClips = content.available === false ? {} : (content.clips || {});
    fixedClipAvailability = Object.keys(fixedClips).length ? 'available' : 'unavailable';
  } catch {
    fixedClips = {};
    fixedClipAvailability = 'unavailable';
  }
  updateFixedClipStatus();
  if (fixedClipAvailability === 'available' && navigator.serviceWorker) {
    try {
      const worker = await navigator.serviceWorker.ready;
      const urls = Object.values(fixedClips).flatMap(clip => [clip.url, clip.fallback_url]);
      worker.active?.postMessage({type: 'cache-fixed-clips', urls});
    } catch { /* Optional offline storage must not change playback availability. */ }
  }
}

function playFixedClip(key) {
  const clip = fixedClips[`${currentLang}:${key}`];
  if (!clip || !appSettings.speak) return;
  stopAudio();
  const player = document.getElementById("ilma-player");
  const url = player.canPlayType?.('audio/ogg; codecs="opus"') ? clip.url : clip.fallback_url;
  playVoiceAudio(url);
}

function syncConnectivity() {
  const offline = navigator.onLine === false;
  // Mic controls stay operable offline: activating one explains that voice needs
  // the internet, which aria-disabled would hide from touch and screen-reader users.
  for (const id of ["home-tap-target", "bank-voice-btn"]) {
    const control = document.getElementById(id);
    control.removeAttribute?.("aria-disabled");
    if (offline) control.setAttribute("aria-describedby", "offline-note"); else control.removeAttribute?.("aria-describedby");
  }
  const note = document.getElementById("offline-note");
  note.textContent = currentLang === "bn" ? "অফলাইন — আগের ব্যাংকের তথ্য দেখা যাবে" : "Offline — saved bank reports are available";
  note.hidden = !offline;
  if (offline && (isListening || recognitionStarting || isSearching)) { stopListening(); showVoiceFallback("offline"); }
}

async function loadBankOptions() {
  try {
    const response = await fetch("/v1/institutions/index");
    if (!response.ok) return;
    const banks = await response.json();
    const select = document.getElementById("bank-select");
    const placeholder = document.createElement("option"); placeholder.value = "";
    placeholder.textContent = currentLang === "bn" ? "ব্যাংক বেছে নিন" : "Choose a bank";
    select.replaceChildren(placeholder);
    banks.forEach(bank => { const option = document.createElement("option"); option.value = String(bank.id); option.textContent = currentLang === "bn" ? bank.name_bn : bank.name_en; select.appendChild(option); });
    select.value = currentBankId == null ? "" : String(currentBankId);
  } catch { /* Existing cached selector/report stays usable offline. */ }
}

async function sendVoiceInput(audio, text, request, choice = null) {
  voiceLanguageReturn=null;voiceLanguageOverride=null;document.getElementById('voice-language-chip').hidden=true;
  const keepTypingOnMiss=!audio&&!choice&&!document.getElementById('agent-text-form').hidden;
  const form = new FormData();
  if (audio) form.append("audio", audio, audio.type.includes("mp4") ? "recording.mp4" : "recording.webm");
  else if (choice) form.append("choice", choice);
  else form.append("text", text);
  form.append("context", JSON.stringify({ ...activeVoiceContext, agent: currentTab === "home", ...(agentConversation ? {conversation: agentConversation} : {}), ui_lang: currentLang, history: voiceHistory.slice(-4), audio_truncated: Boolean(audio?.ilmaTruncated), speak: Boolean(appSettings.speak && (currentTab === 'home' || audio) && (!ivr?.active || ['menu','name','confirm'].includes(ivr.id))), ...(ivr?.active ? { ivr_step: ivr.id } : {}) }));
  const controller = new AbortController();
  voiceAbort = controller;
  const audioRequest = playbackRequest;
  let timeout;
  const armTimeout = ms => { clearTimeout(timeout); timeout = setTimeout(() => controller.abort(), ms); };
  armTimeout(40000); // bounded ASR retries/conversion can precede the first event
  let reader;
  let receivedResult = false, awaitingSpeech = false;
  try {
    const response = await fetch(audio ? "/v1/voice" : "/v1/ask", { method: "POST", body: form, signal: controller.signal, headers: { "Accept-Language": currentLang, "X-ILMA-Device": anonymousDevice } });
    if (response.status === 404 || response.status === 405) throw new Error("voice_backend_outdated");
    if (!response.ok) {
      let result;
      try { result = await response.json(); } catch {}
      throw new Error(result?.error?.code || "voice_unavailable");
    }
    if (!response.body?.getReader) throw new Error("voice_incomplete_response");
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (request !== voiceRequest) { await reader.cancel(); return; }
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      let end;
      while ((end = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, end); buffer = buffer.slice(end + 2);
        const name = block.match(/^event: (.+)$/m)?.[1];
        const data = block.match(/^data: (.+)$/m)?.[1];
        if (request !== voiceRequest) { await reader.cancel(); return; }
        if (data) {
          armTimeout(45000);
          let parsed;
          try { parsed = JSON.parse(data); } catch { throw new Error("voice_incomplete_response"); }
          if(name==='result'&&parsed.type==='agent_turn'&&keepTypingOnMiss&&parsed.conversation?.misses>0)parsed.offer_typing=true;
          await handleVoiceEvent(name, parsed, audioRequest);
          if (name === "result") {receivedResult = true;awaitingSpeech=Boolean(parsed.type==='agent_turn'&&parsed.audio_pending);}
          if (name === 'speech'||name==='speech_unavailable')awaitingSpeech=false;
        }
      }
      if (done) break;
    }
    if (request === voiceRequest && !receivedResult) throw new Error("voice_incomplete_response");
    if (request === voiceRequest && awaitingSpeech) await handleVoiceEvent('speech_unavailable',{},audioRequest);
    if (request === voiceRequest) {
      isSearching = false; voiceAbort = null;
      const player = document.getElementById("ilma-player");
      if (!player.src || player.paused) setWaveformState("idle");
      startExampleCycle();
    }
  } catch (error) {
    if (receivedResult && request === voiceRequest) {
      isSearching = false; voiceAbort = null;
      if(agentPanel?.active){
        document.getElementById('agent-state').textContent=currentLang==='bn'?'অডিও পাওয়া যায়নি। বিকল্প বেছে নিন।':'Audio unavailable. Choose an option.';
        agentPanel.speechUnavailable();
      }else stopAudio();
      document.getElementById("sr-announcer").textContent = currentLang === "bn"
        ? "উত্তরটি পর্দায় আছে। পড়ে শোনানো সম্পূর্ণ হয়নি।" : "The answer is shown. Spoken playback could not finish.";
      startExampleCycle();
      return;
    }
    throw error;
  } finally {
    clearTimeout(timeout); form.delete("audio");
    try { await reader?.cancel(); } catch {}
    reader?.releaseLock?.();
  }
  if (request === voiceRequest && agentPendingResult) { const result = agentPendingResult; agentPendingResult = null; await showAgentTurn(result); }
}

async function handleVoiceEvent(name, data, audioRequest) {
  if (name === "error") throw new Error(data.code);
  if(name==='acknowledgement'){void playGuidedSpeech('agent',null,null,data.audio_url);return;}
  if (name === 'resolved_context') {agentConversation=data.conversation;return;}
  if (name === 'answer_sentence') {
    const live=document.getElementById('voice-live-answer');
    if(live){live.hidden=false;live.textContent=(data.append?live.textContent+' ':'')+data.text;}
    if(agentPanel?.active){const answer=document.getElementById('agent-answer');answer.textContent=(data.append?answer.textContent+' ':'')+data.text;}
    return;
  }
  if (name === "transcript") {
    const live=document.getElementById('voice-live-answer');if(live){live.hidden=true;live.textContent='';}
    lastAgentChoice = "";
    lastVoiceTranscript = data.text;
    if(agentPanel?.active)document.getElementById('agent-heard').textContent=(currentLang==='bn'?'আপনি বলেছেন: ':'You said: ')+data.text;
    if (ivr?.active) document.getElementById("ivr-heard").textContent = (currentLang === "bn" ? "আপনি বলেছেন: " : "You said: ") + data.text;
    if (!voiceLanguageOverride && ['bn','en'].includes(data.language) && currentLang!==data.language) {
      voiceLanguageReturn=currentLang;applyTurnLanguage(data.language);
      const chip=document.getElementById('voice-language-chip');
      chip.textContent=data.language==='bn'?'বাংলায় বলছেন · English-এ থাকুন':'Speaking English · বাংলায় ফিরুন';chip.hidden=false;
    }
    document.getElementById("listening-transcript").textContent = `“${data.text}”`;
    const miniTranscript = document.getElementById("mini-voice-transcript");
    if (miniTranscript) miniTranscript.textContent = `“${data.text}”`;
    const words = document.getElementById("voice-transcript");
    words.textContent = (currentLang === "bn" ? "আপনি বলেছেন: " : "You said: ") + `“${data.text}”`; words.hidden = false;
    document.getElementById("sr-announcer").textContent = currentLang === "bn" ? `আপনি বলেছেন: ${data.text}` : `You said: ${data.text}`;
    if (window.requestAnimationFrame) await new Promise(resolve => window.requestAnimationFrame(() => window.requestAnimationFrame(resolve)));
  }
  if (name === 'result' && data.type === 'agent_turn') {
    const live=document.getElementById('voice-live-answer');if(live){live.hidden=true;live.textContent='';}
    isSearching=false;
    if(data.memory_turn){voiceHistory.push(data.memory_turn);voiceHistory=voiceHistory.slice(-4);}
    if(voiceLanguageOverride&&data.conversation.language!==voiceLanguageOverride){
      agentConversation={...data.conversation,language:voiceLanguageOverride};voiceLanguageOverride=null;
      return sendAgentChoice('repeat');
    }
    await showAgentTurn(data);return;
  }
  if (name === 'speech' && agentPanel?.active) { void agentPanel.deliverSpeech(data);return; }
  if (name === 'speech_unavailable' && agentPanel?.active) {document.getElementById('agent-state').textContent=currentLang==='bn'?'অডিও পাওয়া যায়নি। বিকল্প বেছে নিন।':'Audio unavailable. Choose an option.';agentPanel.speechUnavailable();return;}
  if (ivr?.active && name === 'result') { ivrPendingResult = data; return; }
  if (ivr?.active && name === 'speech') return;
  if (name === "result") {
    voiceFailures = ["clarify", "no_data"].includes(data.type) ? voiceFailures + 1 : 0;
    document.getElementById("home-listening-view").hidden = true;
    document.getElementById("home-idle-view").hidden = false;
    document.getElementById("voice-feedback-message").textContent = (data.privacy_notice ? data.privacy_notice + " " : "") + data.text;
    const allSources = document.getElementById("voice-answer-sources"); allSources.replaceChildren();
    (data.sources || []).forEach((source, index) => {
      if (!/^https?:\/\//i.test(source.source_url || "")) return;
      const link = document.createElement("a"); link.href = source.source_url; link.target = "_blank"; link.rel = "noopener noreferrer";
      link.textContent = (currentLang === "bn" ? "সূত্র: " : "Source: ") + (currentLang==='bn'?(source.source_title_bn||`মূল নথি ${toBnDigits(index+1)}`):(source.source_title_en||source.source_title||source.fact_id||'')); allSources.appendChild(link);
    });
    const list = document.getElementById("voice-matches"); list.replaceChildren();
    if (data.offer_bank_list) {
      const button = document.createElement("button"); button.type = "button"; button.className = "voice-bank-choice";
      button.textContent = currentLang === "bn" ? "ব্যাংকের তালিকা দেখুন" : "See the bank list";
      button.addEventListener("click", () => { closeVoiceFeedback(); currentBankId = null; switchTab("detail"); });
      list.appendChild(button);
    }
    (data.candidates || []).forEach(bank => {
      const button = document.createElement("button"); button.type = "button"; button.className = "voice-bank-choice";
      button.textContent = currentLang === "bn" ? bank.name_bn : bank.name_en;
      button.addEventListener("click", () => { activeVoiceContext = {tab: "bank", bank_id: bank.id}; submitTextQuestion(lastVoiceTranscript); });
      list.appendChild(button);
    });
    if (!data.omit_history && !data.privacy_notice && data.amount_bdt == null && !/[0-9০-৯]|লাখ|হাজার|টাকা|পিন|অ্যাকাউন্ট|\b(?:pin|account|lakh|taka|crore)\b/i.test(lastVoiceTranscript)) {
      voiceHistory.push({ question: lastVoiceTranscript, answer: data.text }); voiceHistory = voiceHistory.slice(-3);
    } else if (data.type === "clarify") {
      voiceHistory.push({ question: "[input omitted]", answer: data.text }); voiceHistory = voiceHistory.slice(-3);
    }
    if (data.type === "report_card") {
      closeMiniVoiceModal();
      document.getElementById("bank-heard").textContent = (currentLang === "bn" ? "আপনি বলেছেন: " : "You said: ") + lastVoiceTranscript;
      document.getElementById("bank-heard").hidden = false;
      openBank(data.institution_id, true);
    }
    else if (["service_answer", "services"].includes(data.type)) {
      closeMiniVoiceModal();
      switchTab("services", true);
      document.getElementById("service-voice-answer").hidden = false;
      document.getElementById("service-heard").textContent = (currentLang === "bn" ? "আপনি বলেছেন: " : "You said: ") + lastVoiceTranscript;
      document.getElementById("service-voice-text").textContent = data.text;
      const verification=document.getElementById("service-voice-verification");verification.textContent=(data.bank_warnings||[]).join(" ");verification.hidden=!data.bank_warnings?.length;
      const sources = document.getElementById("service-voice-sources"); sources.replaceChildren();
      (data.sources || []).forEach(source => {
        const url = source.source_url;
        if (!/^https?:\/\//i.test(url || "")) return;
        const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer";
        link.textContent = source.source_title || (currentLang === "bn" ? "সূত্র" : "Source"); sources.appendChild(link);
      });
      if (data.amount_bdt != null) { document.getElementById("ret-amt-input").value = data.amount_bdt; calculateRealReturn(); }
      if (data.comparison) window.IlmaCatalog?.openComparison(data.comparison,{amount:data.calculator_amount,term:data.calculator_term,fromVoice:true});
    } else {
      closeMiniVoiceModal();
      openVoiceFeedback();
      if (["clarify", "no_data", "not_licensed"].includes(data.type)) showTyping();
    }
  }
  if (name === "speech") playVoiceAudio(data.audio_url, audioRequest);
  if (name === "speech_unavailable") document.getElementById("sr-announcer").textContent = currentLang === "bn" ? "পড়ে শোনানোর সেবা এখন চালু নেই। উত্তরটি পর্দায় আছে।" : "Spoken playback is unavailable. The answer is shown on screen.";
}

async function submitTextQuestion(text = document.getElementById("voice-text-input").value) {
  if (!text.trim()) return;
  lastVoiceTranscript = text.trim();
  stopListening();
  const request = ++voiceRequest; isSearching = true; pauseGreetingCycle();
  setWaveformState("thinking");
  setVoiceState(T[currentLang].checkingText);
  try { await sendVoiceInput(null, text, request); await flushIvrResult(); }
  catch (error) { if (request === voiceRequest) { stopListening(); showVoiceFallback(error.message); } }
}

function openBank(bankId, keepVoiceStream = false) {
  currentBankId = bankId;
  const select = document.getElementById("bank-select");
  if (select) select.value = String(bankId);
  switchTab("detail", keepVoiceStream);
}

async function loadReportCard(bankId) {
  const request = ++reportRequest;
  reportCardData = null;
  document.getElementById("card-bank-name").textContent = bankId ? (currentLang === "bn" ? "একটু অপেক্ষা করুন…" : "Loading…") : (currentLang === "bn" ? "ব্যাংক বেছে নিন" : "Choose a bank");
  document.getElementById("card-bank-meta").textContent = "";
  document.getElementById("card-status-word").textContent = "";
  document.getElementById("card-status-mark").textContent = "";
  document.getElementById("card-status-meaning").textContent = "";
  document.getElementById("scale-marker").className = "scale-marker hidden";
  ["reasons-list", "checks-list", "card-insurance-line"].forEach(id => document.getElementById(id).replaceChildren());
  showReportError("");
  if (!bankId) return;
  try {
    const res = await fetch(`/v1/institutions/${bankId}/report-card`);
    if (!res.ok) throw new Error("Report card load error");
    const data = await res.json();
    if (request !== reportRequest) return;
    reportCardData = data;
    reportCardData._offline = res.headers?.get("X-ILMA-Offline") === "1";
    renderReportCard();
    document.getElementById("card-bank-name").focus({ preventScroll: true });
  } catch (err) {
    if (request !== reportRequest) return;
    const message = navigator.onLine === false
      ? (currentLang === "bn" ? "এই ব্যাংকের তথ্য অফলাইনে নেই। ইন্টারনেট চালু হলে দেখুন।" : "This bank's report is not saved for offline use. Connect to the internet to view it.")
      : (currentLang === "bn" ? "তথ্য লোড করা যায়নি। ব্যাংকের তালিকায় ফিরে আবার চেষ্টা করুন।" : "Could not load data. Go back to the bank list and try again.");
    showReportError(message);
    document.getElementById("sr-announcer").textContent = message;
  }
}

// A failed load hides the status panel and sheet, so no empty card or Listen/Watch buttons remain.
function showReportError(message) {
  const error = document.getElementById("bank-report-error");
  error.textContent = message;
  error.hidden = !message;
  document.getElementById("card-status-panel").hidden = Boolean(message);
  document.getElementById("card-sheet").hidden = Boolean(message);
  if (message) document.getElementById("card-bank-name").textContent = currentLang === "bn" ? "তথ্য পাওয়া যায়নি" : "Report unavailable";
}

const STATUS_WORDS = { strong: ["ঝুঁকি কম", "Low risk"], watch: ["ঝুঁকি মাঝারি", "Medium risk"], high: ["ঝুঁকি বেশি", "High risk"] };
// Short names for the rules behind a card, so the summary repeats its actual reasons.
const REASON_PHRASES = {
  H1: ["নিয়ন্ত্রক পদক্ষেপ", "regulatory action"], H2: ["টাকা তোলায় সীমা", "withdrawal limits"],
  H3: ["মূলধন ঘাটতি", "a capital shortfall"], H4: ["উচ্চ খেলাপি ঋণ", "high bad loans"], H5: ["দুর্বল রেটিং", "a low credit rating"],
  W1: ["খেলাপি ঋণ বেশি", "elevated bad loans"], W2: ["মূলধন ন্যূনতম সীমার কাছাকাছি", "capital close to the minimum"],
  W3: ["রেটিং নিয়ে সতর্কতা", "a rating caution"], W4: ["জরিমানা বা মামলা", "a penalty or legal case"],
  W5: ["প্রভিশন ঘাটতি", "a provision shortfall"], W6: ["লোকসান", "a loss"], W7: ["গড়ের চেয়ে অনেক বেশি আমানতের হার", "deposit rates far above the median"],
  W8: ["জরুরি তারল্য সহায়তা", "emergency liquidity support"], W9: ["শেয়ারের দাম অভিহিত মূল্যের নিচে", "shares trading below face value"]
};

function reasonSummary(reasons, isBn) {
  const phrases = [...new Set((reasons || []).map(reason => REASON_PHRASES[reason.rule]?.[isBn ? 0 : 1]).filter(Boolean))];
  if (!phrases.length) return "";
  const joined = phrases.length === 1 ? phrases[0] : phrases.slice(0, -1).join(", ") + (isBn ? " ও " : " and ") + phrases[phrases.length - 1];
  return isBn ? `${joined}।` : `${joined[0].toUpperCase()}${joined.slice(1)}.`;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
}

function renderReportCard() {
  if (!reportCardData) return;
  const data = reportCardData;
  const noData = { code: "no_data", label_bn: "মূল্যায়ন করা হয়নি", label_en: "Not rated" };
  const status = data.status || noData;
  const isBn = currentLang === "bn";

  document.getElementById("card-bank-name").textContent = isBn ? data.institution.name_bn : data.institution.name_en;
  document.getElementById("card-bank-meta").textContent = isBn
    ? `${data.institution.islamic ? "ইসলামী" : "বাণিজ্যিক"} ব্যাংক · লাইসেন্সপ্রাপ্ত · পূর্ণ বিবরণী · তথ্য তারিখ: ${toBnDigits((data.data_date || "—"))}`
    : `${data.institution.islamic ? "Islamic" : "Commercial"} Bank · Licensed · Full Coverage · Data date: ${data.data_date || "—"}`;

  if (data._offline) document.getElementById("card-bank-meta").textContent += isBn ? " · অফলাইন কপি" : " · Offline copy";
  const statusCode = data.status ? data.status.code : "no_data";
  const markEl = document.getElementById("card-status-mark");
  const wordEl = document.getElementById("card-status-word");
  const meaningEl = document.getElementById("card-status-meaning");

  const marks = { strong: "✓", watch: "⚠", high: "✕", no_data: "" };
  markEl.textContent = marks[statusCode] ?? "";
  wordEl.textContent = isBn ? status.label_bn : status.label_en;
  wordEl.className = `status-word ${statusCode}`;

  if (statusCode === "strong") {
    meaningEl.textContent = isBn ? "আইনি মূলধন পর্যাপ্ত ও খেলাপি ঋণ স্বাভাবিক সীমার মধ্যে রয়েছে।" : "Capital is sound and non-performing loans are well-controlled.";
  } else if (statusCode === "watch") {
    meaningEl.textContent = reasonSummary(data.reasons, isBn) || (isBn ? "কিছু সূচকে সতর্কতা লক্ষ্য করা গেছে, নিয়মিত নজর রাখা প্রয়োজন।" : "Caution indicated in certain metrics; monitoring recommended.");
  } else if (statusCode === "high") {
    meaningEl.textContent = reasonSummary(data.reasons, isBn) || (isBn ? "ঝুঁকির সংকেত পাওয়া গেছে; কারণগুলো নিচে দেখুন।" : "Risk signals were found; see the reasons below.");
  } else {
    meaningEl.textContent = isBn ? "এই ব্যাংকের ঝুঁকি এখনো মূল্যায়ন করা হয়নি। নিচে প্রকাশিত রেটিং দেখুন।" : "This bank’s risk has not been rated. See its published rating below.";
  }

  const marker = document.getElementById("scale-marker");
  marker.className = "scale-marker";
  if (statusCode === "no_data") {
    marker.classList.add("hidden");
  } else {
    marker.classList.add(`pos-${statusCode}`);
  }

  document.getElementById("card-insurance-line").textContent = data.insurance
    ? (isBn ? data.insurance.text_bn : data.insurance.text_en)
    : (isBn ? data.message_bn : data.message_en) || "";

  const reasonsDiv = document.getElementById("reasons-list");
  reasonsDiv.innerHTML = "";
  (data.reasons || []).forEach(r => {
    const card = document.createElement("div");
    card.className = "reason-card";
    card.setAttribute("role", "listitem");
    card.innerHTML = `
      <p class="reason-text">${escapeHTML(isBn ? r.text_bn : r.text_en)}</p>
      <button class="reason-source-link" aria-label="${escapeHTML((isBn ? 'সূত্র দেখুন: ' : 'Show source: ') + (isBn ? r.text_bn : r.text_en))}" data-title="${escapeHTML(r.source_title || (isBn ? 'সূত্র পাওয়া যায়নি' : 'Source unavailable'))}" data-quote="${escapeHTML(r.quote || '')}" data-url="${escapeHTML(r.source_url || '')}" data-page="${escapeHTML(r.page || '')}" data-pub="${escapeHTML(r.published_at || '')}">
        ${T[currentLang].detail.sourceBtn} ${escapeHTML(r.source_title || (isBn ? 'সূত্র পাওয়া যায়নি' : 'Source unavailable'))}${r.checked ? (isBn ? ' · যাচাই করা হয়েছে' : ' · Checked') : ''}
      </button>
    `;
    reasonsDiv.appendChild(card);
  });

  reasonsDiv.querySelectorAll(".reason-source-link").forEach(btn => {
    btn.addEventListener("click", () => {
      openProofModal(
        btn.getAttribute("data-title"),
        btn.getAttribute("data-quote"),
        btn.getAttribute("data-url"),
        btn.getAttribute("data-page"),
        btn.getAttribute("data-pub")
      );
    });
  });

  const checksDiv = document.getElementById("checks-list");
  checksDiv.innerHTML = "";
  (data.checks || []).forEach(c => {
    const item = document.createElement("div");
    item.className = "check-item";
    const statusSign = c.status === "pass" ? "✓" : c.status === "watch" ? "⚠" : c.status === "fail" ? "✕" : "?";
    item.innerHTML = `
      <div class="check-info">
        <span class="check-name">${escapeHTML(isBn ? c.name_bn : c.name_en)}</span>
        <span class="check-desc">${escapeHTML(isBn ? c.desc_bn : c.desc_en)}</span>
      </div>
      <span class="check-badge ${escapeHTML(c.status)}">${statusSign} ${escapeHTML(c.value_text)}</span>
    `;
    checksDiv.appendChild(item);
  });
  window.IlmaCatalog?.reportReady(data);

  const sr = document.getElementById("sr-announcer");
  if (sr) {
    sr.textContent = isBn
      ? `অবস্থা: ${status.label_bn}। কারণ ${toBnDigits((data.reasons || []).length)}টি। ${data.institution.name_bn}।`
      : `Status: ${status.label_en}. ${(data.reasons || []).length} reasons. ${data.institution.name_en}.`;
  }
}

function openProofModal(title, quote, url, page, pubDate, conversionNote = "") {
  const modal = document.getElementById("proof-modal");
  document.getElementById("modal-title").textContent = title || "নথি ও প্রমাণের তথ্য";
  document.getElementById("modal-meta").textContent = currentLang === "bn" ? `পৃষ্ঠা: ${page || "—"} · নথির তারিখ: ${pubDate || "—"}` : `Page: ${page || "—"} · Document date: ${pubDate || "—"}`;
  if (conversionNote) document.getElementById("modal-meta").textContent += ' · ' + conversionNote;

  const quoteDiv = document.getElementById("modal-quote");
  quoteDiv.innerHTML = quote
    ? String(quote).split(/([0-9০-৯][0-9০-৯,.]*)/g).map(part => /^[0-9০-৯]/.test(part) ? `<mark class="quote-highlight">${escapeHTML(part)}</mark>` : escapeHTML(part)).join("")
    : (currentLang === "bn" ? "এই তথ্যের উদ্ধৃতি পাওয়া যায়নি।" : "No source quotation is available.");

  const link = document.getElementById("modal-link");
  if (/^https?:\/\//i.test(url || "")) {
    link.href = url;
    link.style.display = "inline-flex";
  } else {
    link.style.display = "none";
  }
  modalOpener = document.activeElement;
  document.body.style.overflow = "hidden";
  modal.classList.add("open");
  document.querySelector("header").inert = true;
  document.querySelectorAll(".tab-content, .dock").forEach(el => el.inert = true);
  document.getElementById("proof-modal-close").focus();
}

function closeProofModal() {
  document.body.style.overflow = "";
  document.getElementById("proof-modal").classList.remove("open");
  document.querySelectorAll("header, .tab-content, .dock").forEach(el => el.inert = false);
  modalOpener?.focus();
}

function speakReportCard() {
  if(window.IlmaBank?.listenReport)return window.IlmaBank.listenReport();
  if (ivr?.active && currentBankId) return playGuidedSpeech("report_card", null, currentBankId);
  if (currentBankId) return requestReadout("report_card", currentBankId);
}

function calculateInsuranceSplit() {
  const amtInput = document.getElementById("ins-amt-input");
  const typeSelect = document.getElementById("ins-type-select");
  const amt = Math.max(0, parseFloat(amtInput ? amtInput.value : 500000) || 0);
  const type = typeSelect ? typeSelect.value : "bank";

  const resDiv = document.getElementById("ins-result-box");
  if (type === "bank") {
    const insured = Math.min(amt, 200000);
    const uninsured = Math.max(0, amt - 200000);
    resDiv.innerHTML = `
      <div style="font-size: calc(var(--fs) * 1); font-weight: 700; color: var(--good-on-stage); margin-bottom: 6px;">
        ${T[currentLang].services.insuredPart} ${formatTaka(insured)} টাকা (১০০% বীমাযুক্ত)
      </div>
      ${uninsured > 0 ? `
      <div style="font-size: calc(var(--fs) * 1); color: var(--watch-on-stage); margin-bottom: 6px;">
        ${T[currentLang].services.uninsuredPart} ${formatTaka(uninsured)} টাকা
      </div>` : ''}
      <div style="font-size: calc(var(--fs) * .85); color: var(--ink-2);">${T[currentLang].services.payoutNote}</div>
    `;
  } else {
    resDiv.innerHTML = `
      <div style="font-size: calc(var(--fs) * 1); font-weight: 700; color: var(--watch-on-stage); margin-bottom: 6px;">
        ${T[currentLang].services.insuredPart} ${formatTaka(0)} টাকা
      </div>
      <div style="font-size: calc(var(--fs) * .85); color: var(--ink-2);">${T[currentLang].services.nbfiNote}</div>
    `;
  }
}

function calculateRealReturn() {
  const amt = Math.max(0, parseFloat(document.getElementById("ret-amt-input").value) || 0);
  const ratePct = Math.min(25, Math.max(0, parseFloat(document.getElementById("ret-rate-input").value) || 0));
  const tenorMonths = parseInt(document.getElementById("ret-tenor-select").value) || 12;
  const hasTin = document.getElementById("tin-check").checked;

  const grossProfit = amt * (ratePct / 100) * (tenorMonths / 12);
  const taxRate = hasTin ? 0.10 : 0.15;
  const tax = grossProfit * taxRate;
  const netProfit = grossProfit - tax;

  const inflationRate = 0.098;
  const inflationLoss = amt * inflationRate * (tenorMonths / 12);
  const realReturn = netProfit - inflationLoss;

  const resDiv = document.getElementById("ret-result-box");
  resDiv.innerHTML = `
    <div><strong>${T[currentLang].services.grossProfit}</strong> ${formatTaka(grossProfit)} টাকা</div>
    <div><strong>${T[currentLang].services.taxDeducted}</strong> ${formatTaka(tax)} টাকা (${hasTin ? '১০%' : '১৫%'})</div>
    <div><strong>${T[currentLang].services.netProfit}</strong> ${formatTaka(netProfit)} টাকা</div>
    <div style="margin-top: 8px; font-weight: 700; color: ${realReturn >= 0 ? 'var(--good-on-stage)' : 'var(--risk-on-stage)'};">
      ${T[currentLang].services.realReturn} ${formatTaka(realReturn)} টাকা
      <span style="font-size: calc(var(--fs) * .85); font-weight: normal; display: block; color: var(--ink-2); margin-top: 2px;">
        ${realReturn >= 0 ? 'মুদ্রাস্ফীতির চেয়ে বেশি ক্রয়ক্ষমতা অর্জিত হচ্ছে।' : 'মুদ্রাস্ফীতির কারণে প্রকৃত ক্রয়ক্ষমতা হ্রাস পাচ্ছে।'}
      </span>
    </div>
  `;
}

function publicationHTML(row,label) {
  const bn=currentLang==='bn';
  const when=row.date?new Intl.DateTimeFormat(bn?'bn-BD':'en-GB',{day:'numeric',month:'long',year:'numeric'}).format(new Date(row.date+'T00:00:00')):row.year?(bn?toBnDigits(row.year):String(row.year)):'';
  return `<article class="catalog-card publication-card"><p class="catalog-note">${escapeHTML([bn?row.bank_name_bn:row.bank_name_en,label].filter(Boolean).join(' · '))}</p><h2 lang="${/[\u0980-\u09ff]/.test(row.title)?'bn':'en'}">${escapeHTML(row.title)}</h2>${bn&&!/[\u0980-\u09ff]/.test(row.title)?'<p class="catalog-note" lang="bn">মূল শিরোনাম ইংরেজিতে</p>':''}<p>${escapeHTML(when)}</p>${/^https?:\/\//.test(row.source_url)?`<a class="catalog-source" aria-label="${escapeHTML((bn?'উৎস খুলুন: ':'Open source: ')+row.title)}" href="${escapeHTML(row.source_url)}" target="_blank" rel="noopener noreferrer">${row.source_kind==='index'?(bn?'মূল উৎসের সূচি খুলুন ↗':'Open source index ↗'):(bn?'উৎস খুলুন ↗':'Open source ↗')}</a>`:''}</article>`;
}
window.publicationHTML=publicationHTML;

async function loadExtraNews(feed,isBn){
  if(isBn!==(currentLang==='bn'))return;
  document.getElementById('extra-news-sections')?.remove();
  const section=document.createElement('section');section.id='extra-news-sections';feed.after(section);
  try{
    const response=await fetch('/v1/extra-news',{headers:anonymousDevice?{'X-ILMA-Device':anonymousDevice}:{},cache:'no-store'});
    if(!response.ok)throw Error('extra news unavailable');const data=await response.json();
    if(!section.isConnected)return;
    const groups=[['warnings','বাংলাদেশ ব্যাংকের সতর্কবার্তা ও ঘোষণা','BB warnings and notices','বাংলাদেশ ব্যাংকের ঘোষণা','Bangladesh Bank notice'],['rules','নতুন নিয়ম','New rules','বাংলাদেশ ব্যাংকের সার্কুলার','Bangladesh Bank circular'],['announcements','নজরে রাখা ব্যাংকের ঘোষণা','Watched-bank announcements','ডিএসই-তে ব্যাংকের নিজের ঘোষণা','The bank’s own DSE announcement']];
    section.innerHTML=groups.map(([key,bn,en,labelBn,labelEn])=>`<section aria-label="${escapeHTML(isBn?bn:en)}"><h2>${escapeHTML(isBn?bn:en)}</h2>${(data[key]||[]).map(row=>publicationHTML(row,isBn?labelBn:labelEn)).join('')||`<p class="catalog-note">${key==='announcements'&&!data.watching?(isBn?'ব্যাংক ট্যাবে একটি ব্যাংক নজরে রাখুন। ব্যক্তিগত তালিকার ঘোষণাই এখানে দেখানো হবে।':'Watch a bank in the Banks tab to see its announcements here.'):(isBn?'এই বিভাগে সরবরাহকৃত তথ্য নেই।':'No supplied records in this section.')}</p>`}</section>`).join('');
  }catch{section.textContent=isBn?'অতিরিক্ত ঘোষণা লোড করা যায়নি। আবার চেষ্টা করুন।':'Could not load additional notices. Please try again.';}
}

async function loadNews() {
  try {
    const res = await fetch("/v1/news");
    if (!res.ok) throw new Error("News load error");
    const newsItems = await res.json();
    const feed = document.getElementById("news-feed");
    feed.innerHTML = "";
    const isBn = currentLang === "bn";

    if (!newsItems.length) feed.textContent = isBn ? "এখন কোনো সংবাদ নেই।" : "No news available.";
    newsItems.forEach(n => {
      const card = document.createElement("div");
      card.setAttribute("role", "listitem");
      card.style.cssText = "background: var(--paper); border: 1px solid var(--line); border-radius: 16px; padding: 16px; margin-bottom: 14px;";
      card.innerHTML = `
        <span style="display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: calc(var(--fs) * .85); font-weight: 700; background: #E6F4EA; color: #1B5E20; margin-bottom: 8px;">
          ${n.official ? (isBn ? 'সরকারি সূত্র' : 'Official source') : (isBn ? 'খবরে প্রকাশিত, নিশ্চিত নয়' : 'Reported, unconfirmed')}
        </span>
        <h2 style="font-family: var(--display); font-size: calc(var(--fs) * 1.15); font-weight: 700; margin: 0 0 6px; color: var(--ink);">${escapeHTML(isBn ? n.title_bn : n.title_en)}</h2>
        ${isBn&&!/[\u0980-\u09ff]/.test(n.title_bn)?'<p class="catalog-note">খবরটি ইংরেজিতে</p>':''}
        <div style="font-size: calc(var(--fs) * .85); color: var(--ink-2); display: flex; justify-content: space-between;">
          <span>${escapeHTML(n.publisher || '—')}</span>
          <span>${escapeHTML(new Intl.DateTimeFormat(isBn?'bn-BD':'en-GB',{day:'numeric',month:'long',year:'numeric'}).format(new Date(n.date+'T00:00:00')))}</span>
        </div>
        ${/^https?:\/\//i.test(n.source_url || "") ? `<a class="catalog-source" href="${escapeHTML(n.source_url)}" target="_blank" rel="noopener noreferrer">${isBn ? "উৎস খুলুন ↗" : "Open source ↗"}</a>` : ""}
      `;
      feed.appendChild(card);
    });
    await loadExtraNews(feed,isBn);
  } catch (e) {
    document.getElementById("news-feed").textContent = currentLang === "bn" ? "সংবাদ লোড করা যায়নি। আবার চেষ্টা করুন।" : "Could not load news. Try again.";
  }
}

function speakNews() { return requestReadout("news"); }

let phoneLandscape = false;
function syncOrientation() {
  const touch=Boolean(window.matchMedia?.('(pointer: coarse)').matches||navigator.maxTouchPoints>0);
  const type=window.screen?.orientation?.type;
  // Device orientation avoids mistaking a portrait software keyboard for rotation.
  const sideways=type?type.startsWith('landscape'):typeof window.orientation==='number'?Math.abs(window.orientation)===90:Boolean(window.matchMedia?.('(orientation: landscape)').matches);
  const phone=Math.min(window.screen?.width||window.innerWidth||1000,window.screen?.height||window.innerHeight||1000)<=600;
  const active=touch&&sideways&&phone;
  const panel=document.getElementById('orientation-panel');
  if(!panel)return;
  panel.hidden=!active;
  document.querySelector('.scr').inert=active;
  document.querySelector('.scr').classList.toggle('orientation-blocked',active);
  if(active&&!phoneLandscape){if(agentPanel?.active)agentPanel.suspend();if(ivr?.active){ivr.clear();++ivr.epoch;ivr.phase='waiting';}document.querySelectorAll('dialog[open]').forEach(dialog=>dialog.close());closeProofModal();stopListening();stopAudio();pauseGreetingCycle();panel.focus();}
  if(!active&&phoneLandscape){phoneLandscape=false;if(ivr?.active)ivr.enter(ivr.id);else if(appSettings.voiceonly)startGuidedVoice();startExampleCycle();document.querySelector('.dock-item.on')?.focus();}
  phoneLandscape=active;
}

document.addEventListener("DOMContentLoaded", () => {
  updateLocalizedText();
  startExampleCycle();
  syncOrientation();
  window.addEventListener?.('orientationchange',syncOrientation);
  window.addEventListener?.('resize',syncOrientation);
  window.addEventListener?.("resize", fitGreetingLine);
  document.fonts?.ready.then(fitGreetingLine);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { if (agentPanel?.active) agentPanel.suspend(); if (ivr?.active) { ivr.clear(); ++ivr.epoch; ivr.phase = "waiting"; } stopListening(); stopAudio(); pauseGreetingCycle(); }
    else startExampleCycle();
  });
  window.matchMedia?.("(prefers-reduced-motion: reduce)")?.addEventListener?.("change", startExampleCycle);
  document.addEventListener("keydown", (event) => {
    if (!document.getElementById("proof-modal").classList.contains("open")) return;
    if (event.key === "Escape") closeProofModal();
    if (event.key === "Tab") {
      const controls = Array.from(document.querySelectorAll("#proof-modal button, #proof-modal a")).filter(el => el.getClientRects().length);
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  document.getElementById("ilma-player").addEventListener("ended", () => { if (!ivrAudioCancel) stopAudio(); });
  document.getElementById("ilma-player").addEventListener("playing", () => {
    setWaveformState("speaking");
    if(agentPanel?.active){
      const stop=document.getElementById('agent-stop-speech');stop.hidden=false;stop.textContent=currentLang==='bn'?'থামান':'Stop speaking';
      bargeMonitor?.cancel();
      if(window.IlmaBargeMonitor&&appSettings.micExplained){
        const generation=agentPanel.generation;
        bargeMonitor=new window.IlmaBargeMonitor();void bargeMonitor.start(stream=>{
          if(!agentPanel?.active||generation!==agentPanel.generation){stream.getTracks().forEach(t=>t.stop());return;}
          agentPanel.suspend();void startListening(stream);
        });
      }
    }else if(!ivr?.active&&window.IlmaBargeMonitor&&appSettings.micExplained){
      const generation=playbackRequest;
      bargeMonitor?.cancel();bargeMonitor=new window.IlmaBargeMonitor();
      void bargeMonitor.start(stream=>{
        if(generation!==playbackRequest){stream.getTracks().forEach(t=>t.stop());return;}
        stopAudio();void startListening(stream);
      });
    }
    if (!ivr?.active) document.getElementById("sr-announcer").textContent = currentLang === "bn" ? "ইলমা উত্তর পড়ে শোনাচ্ছে।" : "ILMA is reading the answer.";
  });
  document.getElementById("ilma-player").addEventListener("error", () => {
    if(ivrAudioCancel)return; // The ticket player handles bounded retries.
    if (!ivrAudioCancel) stopAudio();
    document.getElementById("sr-announcer").textContent = currentLang === "bn" ? "অডিও চালানো যায়নি। উত্তরটি পর্দায় আছে।" : "Audio could not play. The answer is shown on screen.";
  });
  window.addEventListener?.("offline", syncConnectivity);
  window.addEventListener?.("online", syncConnectivity);
  void loadFixedClips();
  if (navigator.serviceWorker && window.isSecureContext !== false) navigator.serviceWorker.register("/sw.js?v=" + (document.documentElement.dataset?.workerVersion || "legacy")).catch(() => {});
  setupSpeech();

  document.querySelectorAll(".dock button.dock-item").forEach(btn => {
    btn.addEventListener("click", () => {
      if (ivr?.active) ivr.skip();
      const tab = btn.getAttribute("data-tab");
      if (tab === "detail") currentBankId = null;
      if (tab === "home") goHome();
      else switchTab(tab);
    });
  });

  const tapTarget = document.getElementById("home-tap-target");
  if (tapTarget) {
    setupLanguageSwipe(tapTarget);
    let lastRecordingTap = null;
    tapTarget.addEventListener("click", (e) => {
      if (suppressHomeClick) {
        lastRecordingTap = null;
        suppressHomeClick = false;
        e.preventDefault();
        return;
      }
      if (e.target.id === "btn-stop-listening") return;
      if (!isListening) {
        if(isSearching)stopListening();
        lastRecordingTap = null;
        activeVoiceContext = { tab: "home", bank_id: null };
        return startListening();
      }
      // Native keyboard/assistive activations are single click events (detail=0).
      // Do not require two activations from a screen reader or keyboard user.
      if (e.detail === 0) {
        lastRecordingTap = null;
        return finishRecording();
      }
      // Use click timing for touch and mouse alike, without relying on mobile
      // browsers emitting dblclick. Only taps during recording form the pair.
      const now = e.timeStamp ?? Date.now();
      if (lastRecordingTap !== null && now - lastRecordingTap >= 0 && now - lastRecordingTap <= 450) {
        lastRecordingTap = null;
        e.preventDefault();
        return finishRecording();
      }
      lastRecordingTap = now;
    });

  }

  document.getElementById("voice-retry").addEventListener("click", startListening);
  document.getElementById("voice-dialog-close").addEventListener("click", closeVoiceFeedback);
  document.getElementById("voice-feedback").addEventListener("close", () => {
    if (document.getElementById("voice-feedback").open) return;
    document.getElementById("voice-feedback").hidden = true;
    startExampleCycle();
  });

  const stopBtn = document.getElementById("btn-stop-listening");
  if (stopBtn) {
    stopBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (isListening) return finishRecording();
      return stopListening();
    });
  }

  const langBtn = document.getElementById("lang-btn");
  if (langBtn) {
    langBtn.addEventListener("click", toggleLanguage);
  }

  // Unlock on contact, but interrupt only on activation: a touch may become a scroll.
  document.addEventListener("pointerdown", () => {
    window.IlmaAudioSession?.unlock(document.getElementById("ilma-player"));
  }, { capture: true });
  document.addEventListener("click", event => {
    const player = document.getElementById("ilma-player");
    suppressReadoutClick = Boolean(player.src && !player.src.startsWith("blob:") && !player.paused && event.target?.closest?.(".btn-primary-listen"));
    if (!ivr?.active) stopAudio();
  }, { capture: true });
  document.getElementById("voice-type").addEventListener("click", showTyping);
  document.getElementById("voice-text-form").addEventListener("submit", event => { event.preventDefault(); return submitTextQuestion(); });
  document.getElementById("voice-language-chip").addEventListener("click", undoTurnLanguage);
  document.getElementById("mic-permission-allow").addEventListener("click", () => {
    appSettings.micExplained = true; saveSettings(); document.getElementById("mic-permission-dialog").close(); return startListening();
  });
  document.getElementById("mic-permission-later").addEventListener("click", () => { document.getElementById("mic-permission-dialog").close(); showTyping(); });
  for (const [id, tab] of [["bank-voice-btn", "bank"]]) {
    document.getElementById(id).addEventListener("click", () => {
      if (isListening || recognitionStarting || isSearching) stopListening();
      stopAudio();
      activeVoiceContext = { tab, bank_id: tab === "bank" ? currentBankId : null };
      openMiniVoiceModal();
      return startListening();
    });
  }
  const miniStopBtn = document.getElementById("mini-voice-stop");
  if (miniStopBtn) {
    miniStopBtn.addEventListener("click", () => {
      if (isListening) return finishRecording();
      return stopListening();
    });
  }
  const miniCloseBtn = document.getElementById("mini-voice-close");
  if (miniCloseBtn) miniCloseBtn.addEventListener("click", () => stopListening());
  const miniDialog = document.getElementById("mini-voice-modal");
  if (miniDialog) {
    miniDialog.addEventListener("close", () => {
      if (miniDialog.open || miniDialog.hidden) return;
      miniDialog.hidden = true;
      if (isListening || recognitionStarting || isSearching) stopListening();
      else startExampleCycle();
    });
  }
  fetch("/v1/voice/config").then(response => response.ok ? response.json() : null).then(config => { if (config) voiceConfig = config; }).catch(() => {});

  document.querySelectorAll("[data-text-size]").forEach(button => button.addEventListener("click", () => {
    const size = Number(button.dataset.textSize);
    if (![14,16,19,22].includes(size)) return;
    document.documentElement.style.setProperty("--fs", size + "px");
    try { localStorage.setItem("ilma.textSize", String(size)); } catch (_) {}
    updateSettingsText();
  }));
  const settingsDialog = document.getElementById("settings-dialog");
  let voiceOnlyBeforeSettings = appSettings.voiceonly;
  document.getElementById("settings-btn").addEventListener("click", () => {
    voiceOnlyBeforeSettings = appSettings.voiceonly;
    if (agentPanel?.active) agentPanel.suspend();
    stopAudio();
    stopListening();
    pauseGreetingCycle();
    document.getElementById("settings-saved").textContent = "";
    if (ivr?.active) { ivr.clear(); ++ivr.epoch; ivr.phase = "waiting"; }
    settingsDialog.showModal();
  });
  document.getElementById("settings-close").addEventListener("click", () => settingsDialog.close());
  settingsDialog.addEventListener("close", () => {
    if (!appSettings.voiceonly) {
      if (ivr?.active) ivr.skip();
      if (voiceOnlyBeforeSettings && agentPanel?.active) resetAgentConversation();
    } else if (!voiceOnlyBeforeSettings) {
      resetAgentConversation();
      startGuidedVoice();
    } else if (ivr?.active && !document.hidden && !phoneLandscape) {
      ivr.enter(ivr.id);
    }
    if (agentPanel?.active) agentPanel.silent();
    startExampleCycle();
    document.getElementById("settings-btn").focus();
  });
  document.getElementById("settings-language").addEventListener("change", event => setLanguage(event.target.value));
  ["motion", "swipe", "speak", "slow", "voiceonly", "screenreader"].forEach(key => {
    document.getElementById(`settings-${key}`).addEventListener("change", event => {
      appSettings[key] = event.target.checked;
      if (key === "speak" && !appSettings.speak) stopAudio();
      saveSettings();
      updateSettingsText();
      if (key === "motion") startExampleCycle();
      document.getElementById("settings-saved").textContent = currentLang === "bn" ? "সেটিংস সংরক্ষণ করা হয়েছে।" : "Settings saved.";
    });
  });

  const bankSelect = document.getElementById("bank-select");
  if (bankSelect) {
    bankSelect.addEventListener("change", (e) => {
      openBank(parseInt(e.target.value));
    });
  }

  document.getElementById("btn-listen-report").addEventListener("click", speakReportCard);
  document.getElementById("btn-listen-news").addEventListener("click", speakNews);
  document.getElementById("btn-listen-services").addEventListener("click", () => requestReadout("insurance"));

  document.getElementById("btn-watch-bank").addEventListener("click", () => {
    if (window.IlmaCatalog) return window.IlmaCatalog.toggleWatch();
    document.getElementById("sr-announcer").textContent = currentLang === "bn" ? "নজরে রাখার সুবিধা এখনও চালু হয়নি।" : "Bank watching is not available yet.";
  });

  document.getElementById("ins-amt-input").addEventListener("input", calculateInsuranceSplit);
  document.getElementById("ins-type-select").addEventListener("change", calculateInsuranceSplit);
  document.querySelectorAll(".q-pill").forEach(p => {
    p.addEventListener("click", () => {
      document.querySelectorAll(".q-pill").forEach(el => el.classList.remove("active"));
      p.classList.add("active");
      document.getElementById("ins-amt-input").value = p.getAttribute("data-val");
      calculateInsuranceSplit();
    });
  });

  document.getElementById("ret-amt-input").addEventListener("input", calculateRealReturn);
  document.getElementById("ret-rate-input").addEventListener("input", calculateRealReturn);
  document.getElementById("ret-tenor-select").addEventListener("change", calculateRealReturn);
  document.getElementById("tin-check").addEventListener("change", calculateRealReturn);

  document.getElementById("proof-modal-close").addEventListener("click", closeProofModal);
  document.getElementById("proof-close-btn").addEventListener("click", closeProofModal);
  document.getElementById("proof-modal").addEventListener("click", (e) => {
    if (e.target.id === "proof-modal") closeProofModal();
  });

  calculateInsuranceSplit();
  calculateRealReturn();
  setupAgentPanel();
  setupGuidedVoice();
  // Keep the server-rendered loading state until all primary controls, including
  // microphone consent, have handlers. No provider or data request gates this.
  document.getElementById("home-loading").hidden = true;
  document.getElementById("home-idle-view").hidden = !document.getElementById("home-listening-view").hidden;
  if (tapTarget) {
    tapTarget.setAttribute("aria-busy", "false");
    tapTarget.disabled = false;
  }
});

// The label lives in updateSettingsText; the table is shared with timing tests.
function ivrCopy(id) {
  const clip = window.IVR_STEPS[id]?.clip;
  let text = window.IVR_COPY?.[clip]?.[currentLang === 'bn' ? 0 : 1] || '';
  const candidate = ivrCandidates[ivrCandidateIndex];
  return text.replace('{bank}', candidate?.[currentLang === 'bn' ? 'name_bn' : 'name_en'] || '');
}

async function playGuidedSpeech(kind, prompt = null, bankId = currentBankId, audioUrl = null) {
  stopAudio();
  const controller = new AbortController(), player = document.getElementById('ilma-player');
  let resolveAudio, timer, retryTimer;
  const completion = new Promise(resolve => { resolveAudio = resolve; });
  const done = ok => {
    clearTimeout(timer); clearTimeout(retryTimer); controller.abort();
    player.removeEventListener('ended', ended); player.removeEventListener('error', failed);
    if (ivrAudioCancel === cancelled) ivrAudioCancel = null;
    resolveAudio(ok);
  };
  const ended = () => {lastSpeechEndedAt=performance.now();done(true);}, failed = () => done(false), cancelled = () => done(false);
  ivrAudioCancel = cancelled;
  timer = setTimeout(failed, 90000);
  player.addEventListener('ended', ended); player.addEventListener('error', failed);
  (async () => {
    try {
      const clip = prompt !== 'ivr_confirm' && fixedClips[`${currentLang}:${prompt}`];
      let url = audioUrl || clip && (player.canPlayType?.('audio/ogg; codecs="opus"') ? clip.url : clip.fallback_url);
      if (!url) {
        if (kind === 'agent') throw Error('speech_unavailable');
        const response = await fetch('/v1/speech', { method: 'POST', signal: controller.signal,
          headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind, prompt, institution_id: bankId, language: currentLang }) });
        if (!response.ok) throw Error('speech_unavailable');
        url = (await response.json()).audio_url;
      }
      if (controller.signal.aborted) return;
      if (!(url?.startsWith('data:audio/mpeg;base64,') || (/^\/static\/audio\/fixed\/[a-zA-Z0-9_-]+\.(?:opus|mp3)$/.test(url || '') || /^\/v1\/audio\/[A-Za-z0-9_-]{32}\.mp3$/.test(url || '')))) throw Error('speech_unavailable');
      if(/^\/v1\/audio\/[A-Za-z0-9_-]{32}\.mp3$/.test(url)){
        const until=Date.now()+45000;
        while(!controller.signal.aborted){
          const statusResponse=await fetch(url.replace(/\.mp3$/,'/status'),{signal:controller.signal,cache:'no-store'});
          if(!statusResponse.ok)throw Error('speech_unavailable');
          const status=await statusResponse.json();
          if(['ready','streaming'].includes(status.state))break;
          if(status.state==='unavailable'||Date.now()>=until)throw Error('speech_unavailable');
          await new Promise(resolve=>{retryTimer=setTimeout(resolve,Math.max(100,Math.min(3000,(status.retry_after||1)*1000)));controller.signal.addEventListener('abort',resolve,{once:true});});
        }
      }
      if(controller.signal.aborted)return;
      player.src = url; player.playbackRate = appSettings.slow ? .85 : 1;
      await player.play();
    } catch { done(false); }
  })();
  return completion;
}

async function flushIvrResult() {
  if (!ivr?.active || !ivrPendingResult) return;
  const result = ivrPendingResult; ivrPendingResult = null;
  if (result.ivr_action) return ivr.command(result.ivr_action);
  if (result.candidates?.length) {
    ivrCandidates = result.candidates; ivrCandidateIndex = 0; return ivr.enter('confirm');
  }
  if (result.type === 'report_card') {
    currentBankId = result.institution_id;
    appSettings.ivrFinished = true; saveSettings();
    openBank(currentBankId, true); return ivr.enter('report');
  }
  document.getElementById('ivr-status').textContent = result.text || '';
  ivr.silent();
}

async function guidedAction(action) {
  if (!ivr?.active) return;
  if (['mic', 'name', 'report', 'next'].includes(action)) return ivr.enter(action);
  if (action === 'permission') {
    activeVoiceContext = { tab: 'home', bank_id: null };
    return startListening();
  }
  if (action === 'bn' || action === 'en') {
    setLanguage(action, false); appSettings.ivrLanguageChosen = true; saveSettings();
    const epoch = ++ivr.epoch;
    await playGuidedSpeech('ivr', action === 'bn' ? 'ivr_chose_bn' : 'ivr_chose_en', null);
    if (ivr.active && epoch === ivr.epoch) return ivr.enter('menu');
  }
  if (action === 'bank' || action === 'services') {
    const epoch = ++ivr.epoch;
    await playGuidedSpeech('ivr', action === 'bank' ? 'ivr_chose_bank' : 'ivr_chose_services', null);
    if (!ivr.active || epoch !== ivr.epoch) return;
    if (action === 'bank') return ivr.enter('name');
    ivr.skip(); switchTab('services'); return;
  }
  if (action === 'listen') {
    ivr.phase = 'starting'; await startListening();
    if (ivr.active && isListening) ivr.phase = 'listening'; return;
  }
  if (action === 'no') {
    ivrCandidateIndex++;
    return ivr.enter(ivrCandidateIndex < ivrCandidates.length ? 'confirm' : 'name');
  }
  if (action === 'yes') {
    const bank = ivrCandidates[ivrCandidateIndex];
    if (!bank) return ivr.enter('name');
    activeVoiceContext = { tab: 'bank', bank_id: bank.id };
    ivr.phase = 'searching';
    return submitTextQuestion(bank[currentLang === 'bn' ? 'name_bn' : 'name_en']);
  }
}

function startGuidedVoice() {
  if (!ivr || !appSettings.voiceonly || document.hidden || phoneLandscape) return;
  stopListening(); switchTab('home'); pauseGreetingCycle();
  playTone(660, .08);
  return ivr.enter('open');
}

function setupGuidedVoice() {
  if (!window.IlmaGuidedVoice) return;
  ivr = new window.IlmaGuidedVoice({
    cancel() { ivrPendingResult = null; stopListening(); },
    interrupt: stopAudio,
    recording: () => isListening,
    assistive: () => appSettings.screenreader,
    finish: finishRecording,
    render(id) {
      document.getElementById('ivr-overlay').hidden = false;
      document.getElementById('main-content').classList.add('ivr-active');
      document.querySelectorAll('.tab-content').forEach(el => { el.inert = true; });
      const text = id === 'report' ? (currentLang === 'bn' ? 'ব্যাংকের অবস্থা পড়ে শোনাচ্ছি।' : 'Reading the bank report.') : ivrCopy(id);
      document.getElementById('ivr-question').textContent = text;
      document.getElementById('ivr-tap').setAttribute('aria-label', text);
      document.getElementById('ivr-status').textContent = '';
      document.getElementById('ivr-skip').textContent = currentLang === 'bn' ? 'এড়িয়ে যান' : 'Skip';
      document.getElementById('ivr-tap').focus(); pauseGreetingCycle();
    },
    announce(id) { document.getElementById('sr-announcer').textContent = ivrCopy(id); },
    async prompt(id) {
      const epoch = ivr.epoch;
      if (id === 'report') return speakReportCard();
      if (id === 'open' && appSettings.voiceonly) await playGuidedSpeech('ivr', 'ivr_ready', null);
      if (!ivr.active || epoch !== ivr.epoch) return false;
      const heard = await playGuidedSpeech('ivr', window.IVR_STEPS[id].clip,
        id === 'confirm' ? ivrCandidates[ivrCandidateIndex]?.id : null);
      if (!heard && ivr.active) document.getElementById('ivr-status').textContent = currentLang === 'bn'
        ? 'শুনতে পাওয়া যায়নি। এক বা দুইবার চাপুন, অথবা এড়িয়ে যান।' : 'Audio unavailable. Tap once or twice, or Skip.';
      return heard;
    },
    async listen(id) {
      if (document.hidden || phoneLandscape || navigator.onLine === false) { ivr.silent(); return; }
      activeVoiceContext = { tab: id === 'next' ? 'bank' : 'home', bank_id: id === 'next' ? currentBankId : null };
      await startListening();
    },
    async echo(n, id) {
      navigator.vibrate?.(30);
      // Transition prompts echo menu/language choices; other choices use fixed yes/no.
      if (!['language','menu'].includes(id)) await playGuidedSpeech('ivr', n === 1 ? 'ivr_yes' : 'ivr_no', null);
    },
    action: guidedAction,
    async read(kind) {
      if (!['reasons','insurance','sources'].includes(kind) || !currentBankId) return ivr.enter(ivr.id);
      ivr.clear(); const epoch = ++ivr.epoch; ivr.phase = 'speaking';
      await playGuidedSpeech(kind, null, currentBankId);
      if (ivr.active && epoch === ivr.epoch) return ivr.enter('next');
    },
    exit() {
      appSettings.ivrFinished = true; saveSettings();
      document.getElementById('ivr-overlay').hidden = true;
      document.getElementById('main-content').classList.remove('ivr-active');
      document.querySelectorAll('.tab-content').forEach(el => { el.inert = false; });
      activeVoiceContext = { tab: 'home', bank_id: null };
      switchTab('home'); startExampleCycle(); document.getElementById('home-tap-target').focus();
    }
  });
  document.getElementById('ivr-tap').addEventListener('click', event => ivr.tap(event));
  document.getElementById('ivr-skip').addEventListener('click', () => ivr.skip());
  // The optional native wrapper may implement this bridge. No UA heuristics.
  const bridge = window.Capacitor?.Plugins?.IlmaAccessibility;
  if (bridge?.isTouchExplorationEnabled) bridge.isTouchExplorationEnabled().then(result => {
    if (result.enabled) { appSettings.screenreader = true; updateSettingsText(); }
  }).catch(() => {});
  if (appSettings.voiceonly) startGuidedVoice();
}

function hideAgentConversation() {
  agentConversation = null; agentPendingResult = null; lastAgentChoice = '';
  document.getElementById('agent-text-input').value='';document.getElementById('agent-text-form').hidden=true;
  document.getElementById('agent-panel').hidden = true;
  document.getElementById('tab-home').classList.remove('agent-open');
  startExampleCycle();
  // Leaving by any route drops the answer's history entry, so Back never returns to it.
  if (window.history?.state?.ilmaAnswer) window.history.back();
}

// The answer lives inside the Home tab, so every way home goes through here.
function goHome() {
  stopListening(); stopAudio();
  if (agentConversation || agentPanel?.active || !document.getElementById('agent-panel').hidden) resetAgentConversation();
  activeVoiceContext = { tab: 'home', bank_id: null };
  switchTab('home');
}

function setupBackToHome() {
  window.addEventListener?.('popstate', () => { if (!document.getElementById('agent-panel').hidden) goHome(); });
  // Only a native wrapper provides this; the web app has its browser Back.
  window.Capacitor?.Plugins?.App?.addListener?.('backButton', () => {
    if (document.getElementById('agent-panel').hidden) window.Capacitor.Plugins.App.minimizeApp?.();
    else goHome();
  });
}

function resetAgentConversation() {
  if (agentPanel?.active) agentPanel.reset();
  else hideAgentConversation();
}

function showAgentSource(source) {
  agentPanel?.suspend(); stopListening(); stopAudio();
  const date = source.published_at ? new Intl.DateTimeFormat(currentLang === 'bn' ? 'bn-BD' : 'en-GB', {dateStyle:'long'}).format(new Date(source.published_at+'T00:00:00')) : '';
  openProofModal(source.source_title || (currentLang === 'bn' ? 'অবস্থার নিয়ম ও সূত্র' : 'Status rules and sources'),source.quote || (source.inputs || []).map(row => row[currentLang === 'bn' ? 'text_bn' : 'text_en']).join('\n'),source.source_url,source.page ? (currentLang === 'bn' ? toBnDigits(source.page) : source.page) : null,date,
    currentLang === 'bn' ? 'মূল পাতার হাইলাইট করা ছবি পাওয়া যাচ্ছে না।' : 'A highlighted source-page image is unavailable.');
}

async function showAgentTurn(result) {
  if(['bn','en'].includes(result.language)&&result.language!==currentLang)applyTurnLanguage(result.language);
  const guided = Boolean(ivr?.active || agentPanel?.guided);
  if (ivr?.active) {
    ivr.active = false; ++ivr.epoch; ivr.clear(); ivrPendingResult = null;
    document.getElementById('ivr-overlay').hidden = true;
    document.getElementById('main-content').classList.remove('ivr-active');
    document.querySelectorAll('.tab-content').forEach(el => { el.inert = false; });
    appSettings.ivrFinished = true; saveSettings();
  }
  if (currentTab !== 'home') switchTab('home');
  agentConversation = result.conversation;
  if (window.history?.pushState && !window.history.state?.ilmaAnswer) window.history.pushState({ ilmaAnswer: true }, '');
  if (agentPanel) {
    // Result text renders immediately; streamed speech is delivered separately.
    void agentPanel.show(result,guided);
  }
}

async function sendAgentChoice(choice) {
  if (!agentConversation) return;
  lastAgentChoice = agentPanel?.result?.next?.options.find(option => option.value === choice)?.label || choice;
  stopListening(); stopAudio();
  const request = ++voiceRequest; isSearching = true;
  document.getElementById('agent-state').textContent = T[currentLang].checkingText;
  try { await sendVoiceInput(null,null,request,choice); }
  catch (error) { if (request === voiceRequest) { stopListening(); showVoiceFallback(error.message); } }
}

let lastSpeechEndedAt=0;
function setupAgentPanel() {
  if (!window.IlmaAgentPanel) return;
  agentPanel = new window.IlmaAgentPanel({
    cancel: stopListening, interrupt: stopAudio,
    offerReplay(){document.getElementById('agent-repeat').textContent=currentLang==='bn'?'আবার শুনুন':'Listen again';document.getElementById('agent-state').textContent=currentLang==='bn'?'উত্তর প্রস্তুত। আবার শুনুন চাপলে শুনতে পাবেন।':'The answer is ready. Choose Listen again to hear it.';},
    recording: () => isListening, finish: finishRecording,
    assistive: () => appSettings.screenreader,
    send: sendAgentChoice,
    typing() {
      document.getElementById('agent-text-form').hidden=false;
      document.getElementById('agent-state').textContent=currentLang==='bn'?'কথা শোনা যায়নি। বিকল্প বেছে নিন অথবা লিখে বলুন।':'Could not hear a reply. Choose an option or type your question.';
      document.getElementById('agent-text-input').focus();
    },
    async listen() {
      const generation=agentPanel.generation;
      const echoDelay=lastSpeechEndedAt?Math.max(0,300-(performance.now()-lastSpeechEndedAt)):0;
      if(echoDelay)await new Promise(resolve=>setTimeout(resolve,echoDelay));
      if(!agentPanel.active||generation!==agentPanel.generation)return;
      if (document.hidden || phoneLandscape || currentTab !== 'home') return;
      activeVoiceContext = {tab:'home',bank_id:null};
      return startListening();
    },
    async play(audio) {
      const generation=agentPanel.generation;
      for(const url of (Array.isArray(audio)?audio:[audio])) {
        if(!agentPanel.active||generation!==agentPanel.generation)return false;
        if(!await playGuidedSpeech('agent',null,null,url))return false;
      }
      return true;
    },
    async question(state) {
      if(!appSettings.speak&&!appSettings.voiceonly)return false;
      stopAudio();
      const request = playbackRequest;
      try {
        const response = await fetch('/v1/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'agent_question',agent_state:state,language:currentLang})});
        if (!response.ok || request !== playbackRequest) return false;
        const data = await response.json();
        if (request !== playbackRequest) return false;
        return playGuidedSpeech('agent',null,null,data.audio_url);
      } catch { return false; }
    },
    render(result) {
      const bn = currentLang === 'bn';
      document.getElementById('tab-home').classList.add('agent-open');
      document.getElementById('agent-panel').hidden = false;
      document.getElementById('agent-heard').textContent = lastAgentChoice ? (bn ? 'আপনি বেছেছেন: ' : 'You chose: ')+lastAgentChoice : lastVoiceTranscript ? (bn ? 'আপনি বলেছেন: ' : 'You said: ')+lastVoiceTranscript : '';
      document.getElementById('agent-answer').textContent=result.speech||result.text;
      document.getElementById('agent-card-label').textContent=bn?'সঠিক অঙ্ক ও সূত্র দেখুন':'See exact figures and sources';
      document.getElementById('agent-card').open=false;
      const sentences = document.getElementById('agent-sentences'); sentences.replaceChildren();
      for (const sentence of result.sentences) {
        const article = document.createElement('article'),text = document.createElement('p');
        text.textContent = sentence.text; article.appendChild(text);
        for (const id of sentence.fact_ids) {
          const fact = result.facts.find(f => f.fact_id === id);
          if (fact?.status) { const chip = document.createElement('span'); chip.className = 'agent-chip';chip.textContent = fact.status[bn ? 'label_bn' : 'label_en'] || (bn ? 'অবস্থা যাচাই হয়নি' : 'Condition unverified');article.appendChild(chip); }
          const button = document.createElement('button'); button.type = 'button';button.className = 'agent-source';button.textContent = bn ? 'সূত্র ›' : 'Source ›';
          button.addEventListener('click',() => showAgentSource(fact?.source || sentence.source || {})); article.appendChild(button);
        }
        sentences.appendChild(article);
      }
      document.getElementById('agent-check-label').textContent = result.checked === 'model' ? (bn ? 'সূত্র মিলিয়ে যাচাই করা হয়েছে' : 'Claims checked against cited facts') : (bn ? 'সূত্রের তথ্য সহজ করে বোঝানো হয়েছে' : 'Explained using sourced facts');
      document.getElementById('agent-question').textContent = bn?'ট্যাপ করে উত্তর দিন':'Tap to reply';
      document.getElementById('agent-state').textContent = result.audio_pending || /^data:audio\//.test(result.speech||'') ? '' : (bn ? 'অডিও পাওয়া যাচ্ছে না। বিকল্প বেছে নিন।' : 'Audio unavailable. Choose an option.');
      const options = document.getElementById('agent-options'); options.replaceChildren();
      for (const option of result.next.options.slice(0,4)) {
        const button = document.createElement('button');button.type = 'button';button.textContent = option.label;
        button.addEventListener('click',()=>agentPanel.choose(option.value)); options.appendChild(button);
      }
      const labels = {'agent-home':bn?'← হোম':'← Home','agent-report':bn?'পুরো রিপোর্ট দেখুন':'View full report','agent-repeat':bn?'আবার':'Repeat','agent-end':bn?'শেষ':'Finish'};
      for (const [id,text] of Object.entries(labels)) document.getElementById(id).textContent = text;
      document.getElementById('agent-report').hidden = !result.conversation.institution_id;
      document.getElementById('agent-text-form').hidden=!result.offer_typing;
      document.getElementById('agent-text-label').textContent=bn?'লিখে বলুন':'Type your question';
      document.getElementById('agent-text-submit').textContent=bn?'খুঁজুন':'Search';
      document.getElementById('agent-tap').setAttribute('aria-label',bn?'ট্যাপ করে উত্তর দিন':'Tap to reply');
      const names = bn ? ['শুনেছি','বুঝেছি','খুঁজেছি','লিখেছি','যাচাই করেছি'] : ['Heard','Understood','Retrieved','Worded','Checked'];
      const trace = document.getElementById('agent-trace');trace.replaceChildren();
      for (const [index,step] of result.trace.steps.entries()) {
        const li = document.createElement('li');
        const status = step.status === 'ok' ? (bn?'সম্পন্ন':'complete') : step.status === 'skipped' ? (bn?'দরকার হয়নি':'not needed') : step.status === 'template' ? (bn?'নির্দিষ্ট ভাষা':'template') : (bn?'পাওয়া যায়নি':'unavailable');
        li.textContent = `${names[index] || step.stage}: ${step.model} · ${bn ? toBnDigits(step.ms) : step.ms} ${bn?'মিলিসেকেন্ড':'ms'} · ${status}${step.tool ? ' · '+step.tool : ''}${step.fact_count != null ? ' · '+(bn ? toBnDigits(step.fact_count)+'টি তথ্য' : step.fact_count+' facts') : ''}`;
        trace.appendChild(li);
      }
      document.getElementById('agent-rule-notice').textContent = result.trace.status_rule_notice;
      const audio = result.trace.audio;
      document.getElementById('agent-audio-note').textContent = audio?.duration_ms ? (bn ? 'অডিও: '+toBnDigits((audio.duration_ms/1000).toFixed(1))+' সেকেন্ড' : 'Audio: '+(audio.duration_ms/1000).toFixed(1)+' seconds') + (audio.status === 'over_target' ? (bn ? ' · লক্ষ্যের চেয়ে দীর্ঘ' : ' · longer than target') : '') : '';

      document.getElementById('main-content').scrollTop = 0;
      document.getElementById('sr-announcer').textContent = result.speech||result.text;
      if(result.offer_typing)document.getElementById('agent-text-input').focus();else document.getElementById('agent-tap').focus({preventScroll:true}); pauseGreetingCycle();
      if (result.action?.type === 'open_report') openBank(result.action.institution_id);
      if (result.action?.type === 'open_proof') showAgentSource(result.action.source);
    },
    exit: hideAgentConversation
  });
  document.getElementById('agent-text-form').addEventListener('submit',event=>{event.preventDefault();const input=document.getElementById('agent-text-input');if(!input.value.trim())return;stopAudio();void submitTextQuestion(input.value);});
  document.getElementById('agent-stop-speech').addEventListener('click',()=>agentPanel.suspend());
  document.getElementById('agent-tap').addEventListener('click',event=>agentPanel.tap(event));
  document.getElementById('agent-home').addEventListener('click', goHome);
  setupBackToHome();
  for (const [id,choice] of [['agent-report','report'],['agent-repeat','repeat'],['agent-end','end']]) document.getElementById(id).addEventListener('click',()=>agentPanel.choose(choice));
}
