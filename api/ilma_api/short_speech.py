"""Polite next questions and a single coherent narration paragraph."""
QUESTIONS={
 'BANK':('কারণ নাকি সেবা শুনবেন?','Hear details or services?'),
 'DETAIL':('হিসাব শুনবেন, নাকি আগের ঘটনা?','Hear figures, or past events?'),
 'FIGURES':('সেবা দেখবেন, নাকি অন্য ব্যাংক?','See services, or ask another bank?'),
 'HISTORY':('সেবা দেখবেন, নাকি অন্য ব্যাংক?','See services, or ask another bank?'),
 'SERVICES':('কোন সেবা জানতে চান?','Which service would you like?'),
 'SERVICE':('অন্য ব্যাংকের সাথে মিলিয়ে দেখবেন?','Compare with another bank?'),
 'COMPARE':('প্রথম ব্যাংকের অবস্থা শুনবেন?','Hear the first bank’s condition?'),
 'NEXT':('অন্য ব্যাংকের কথা শুনবেন?','Ask about another bank?'),
 'ASK_BANK':('কোন ব্যাংকের কথা জানতে চান?','Which bank would you like?'),
 'WATCH_CONFIRM':('সতর্কবার্তা ছাড়াই নজরে রাখবেন?','Watch this bank without notifications?')}

def parts(db,facts,conversation,question,tool,action=None):
 from ilma_api.answer_wording import compose
 return [compose(db,facts,conversation,question,tool,action).speech]
