"""Polite next questions and a single coherent narration paragraph."""
QUESTIONS={
 'BANK':('কেন এমন বললাম আরও শুনবেন, নাকি এই ব্যাংকের সেবা দেখবেন?','Would you like to hear the reasons, or see this bank’s services?'),
 'DETAIL':('ব্যাংকের আয় ব্যয়ের হিসাব শুনবেন, নাকি আগে কোনো ঘটনা ঘটেছে কি না?','Would you like to hear the financial figures, or its past events?'),
 'FIGURES':('এই ব্যাংকের সেবা দেখবেন, নাকি অন্য কোনো ব্যাংকের কথা জানতে চান?','Would you like to see this bank’s services, or ask about another bank?'),
 'HISTORY':('এই ব্যাংকের সেবা দেখবেন, নাকি অন্য কোনো ব্যাংকের কথা জানতে চান?','Would you like to see this bank’s services, or ask about another bank?'),
 'SERVICES':('কোন সেবার কথা জানতে চান, এফডিআর, ডিপিএস, কার্ড নাকি গৃহঋণ?','Which service would you like to hear about, FDR, DPS, cards or home loans?'),
 'SERVICE':('অন্য ব্যাংকের সাথে মিলিয়ে দেখবেন?','Would you like to compare it with other banks?'),
 'COMPARE':('প্রথম ব্যাংকের অবস্থা সম্পর্কে শুনতে চান?','Would you like to hear about the first bank’s condition?'),
 'NEXT':('আর কোনো ব্যাংকের কথা জানতে চান?','Would you like to ask about another bank?'),
 'ASK_BANK':('কোন ব্যাংকের কথা জানতে চান, নাম বলবেন?','Which bank would you like to ask about?'),
 'WATCH_CONFIRM':('এই ব্যাংক নজরে রাখার তালিকায় রাখবেন? সতর্কবার্তা পাঠানো এখনও চালু নেই।','Would you like to watch this bank? Notifications are not available yet.')}

def parts(db,facts,conversation,question,tool,action=None):
 from ilma_api.answer_wording import compose
 return [compose(db,facts,conversation,question,tool,action).speech]
