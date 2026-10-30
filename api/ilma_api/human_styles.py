"""Wording alternatives for code-computed meanings, never new claims."""
from ilma_api.human_tokens import low_npl

def alternatives(f,language):
    bn=language=='bn';v=f.get('values',{});metric=v.get('metric')
    if f.get('kind')=='status' and f.get('status',{}).get('code')=='strong':
        return (['অবস্থা ভালো, বর্তমান সূচকগুলো ইতিবাচক','আর্থিক সূচক অনুযায়ী এখন ভালো অবস্থায় আছে','বর্তমান হিসাবগুলো ভালো অবস্থার দিকেই ইঙ্গিত করছে','প্রকাশিত সূচকে সামগ্রিক অবস্থা ভালো দেখা যাচ্ছে','হালনাগাদ মূল্যায়নে ভালো অবস্থার লক্ষণ আছে'] if bn else ['is in good condition based on the current indicators','currently shows a good position in its published indicators','has indicators pointing to good condition','looks in good condition on the available financial measures','shows a good overall position in the current assessment'])
    if metric=='crar' and f.get('kind')=='figure' and v.get('value',0)*100>=v.get('minimum_percent',12.5):
        return ([
          'নিজের মূলধন ন্যূনতম চাহিদার ওপরে আছে, তাই ক্ষতি সামলানোর বাড়তি জায়গা আছে',
          'আইনে যতটা মূলধন লাগে তার চেয়ে বেশি আছে, যা কিছুটা লোকসান সামলাতে সাহায্য করে',
          'ক্ষতি হলে ব্যবহারের জন্য ন্যূনতমের চেয়ে বাড়তি নিজস্ব অর্থ রয়েছে',
          'সম্ভাব্য লোকসান মোকাবিলায় নিজের অর্থ বাধ্যতামূলক সীমার ওপরে আছে',
          'দরকারের চেয়ে বেশি নিজস্ব তহবিল আছে, ফলে ক্ষতি নেওয়ার কিছু সামর্থ্য রয়েছে',
          'লোকসান সামাল দেওয়ার নিজের অর্থের ভাণ্ডার ন্যূনতম প্রয়োজন ছাড়িয়ে আছে',
          'নিয়মের চাহিদা মিটিয়েও হাতে নিজের কিছু বাড়তি মূলধন আছে',
          'ক্ষতি মোকাবিলার নিজস্ব তহবিল নিয়ম অনুযায়ী প্রয়োজনীয় পরিমাণের চেয়ে বেশি',
          'নিজস্ব অর্থের হিসাবে ন্যূনতম চাহিদার ঘাটতি নেই, বরং বাড়তি জায়গা আছে'
        ] if bn else [
          'its own capital exceeds the minimum, giving it extra capacity to absorb losses',
          'it holds more of its own money than required, providing some room for losses',
          'its own funds stand above the required level, adding loss-absorbing capacity',
          'there is extra capital beyond the minimum requirement to help handle losses',
          'its capital requirement is met with additional resources left to absorb losses',
          'the bank has an extra cushion of its own funds above the required amount',
          'its own financial resources exceed the minimum needed for the risks it takes',
          'the required capital level is covered with additional room for potential losses',
          'its own capital has room above the threshold rather than a shortfall'
        ])
    if metric=='npl_ratio' and f.get('kind')=='figure' and low_npl(v.get('value',1)):
        return ([
          'দেওয়া ঋণের খুব সামান্য অংশ নিয়ে পরিশোধের সমস্যা হচ্ছে, যা ভালো লক্ষণ',
          'ঋণের বেশির ভাগ খেলাপি হিসেবে চিহ্নিত নয়, যা ইতিবাচক',
          'খেলাপি হওয়া ঋণের অংশ ছোট, ফলে ঋণের মানে ভালো লক্ষণ দেখা যায়',
          'মোট ঋণের তুলনায় সমস্যায় পড়া অংশ খুব কম, যা আশাব্যঞ্জক সূচক',
          'অল্প অংশের ঋণ ফেরত পেতে জটিলতা হচ্ছে, এই হিসাবটি অনুকূল'
        ] if bn else [
          'only a small share of lending has repayment problems, a positive sign',
          'problem lending forms a small part of the total, which is encouraging',
          'the portion of loans with overdue repayments is low, an encouraging indicator',
          'relatively little of its lending is classified as problematic, a positive feature',
          'repayment trouble affects a small portion of the loan book, a favourable sign'
        ])
    return []
