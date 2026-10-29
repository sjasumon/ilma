"""Authored glossary text from FRD §21.2, not model-generated financial facts.

An entry's optional fourth value is its content version; corrected wording gets a
new version so existing databases pick it up while the old row stays auditable.
"""
TERMS = [
    (['net profit', 'নিট মুনাফা'], 'আয় থেকে সব খরচ ও কর বাদ দেওয়ার পর অবশিষ্ট লাভ।', 'The profit remaining after expenses and taxes.'),
    (['median', 'মধ্যমান'], 'অঙ্কগুলো ছোট থেকে বড় সাজালে মাঝের মান; জোড় সংখ্যক অঙ্ক হলে মাঝের দুটির গড়।', 'The middle value after sorting; for an even number of values, the average of the middle two.'),
    (['capital buffer', 'বাফার'], 'মূলধনের ন্যূনতম চাহিদার ওপরে অতিরিক্ত মূলধন, যা ক্ষতি সামলানোর জায়গা বাড়ায়।', 'Extra capital above the minimum requirement, adding capacity to absorb losses.'),
    (['npl', 'খেলাপি ঋণ', 'খারাপ ঋণ', 'bad loans', 'problem loans'], 'যে ঋণের কিস্তি নির্ধারিত সময় পেরিয়েও ফেরত আসেনি; মোট ঋণের শতাংশ হিসেবে দেখানো হয়।', 'Loans whose repayments are overdue beyond the set period, shown as a share of total loans.', 3),
    (['crar', 'capital adequacy', 'capital ratio', 'মূলধন'], 'ব্যাংক কতটা ঝুঁকি নিচ্ছে, তার তুলনায় নিজের টাকা কতটা আছে, সেই হিসাব; বেশি হলে ক্ষতি সামলানোর জায়গা বেশি।', 'The bank’s own money relative to the risks it takes; a higher ratio gives more capacity to absorb losses.', 3),
    (['provision', 'প্রভিশন'], 'ক্ষতির আশঙ্কায় আগে থেকে আলাদা করে রাখা টাকা।', 'Money set aside in advance for possible losses.'),
    (['deposit insurance', 'আমানত বিমা', 'আমানত বীমা'], 'ব্যাংক বন্ধ হলে আইন অনুযায়ী সর্বোচ্চ যত টাকা ফেরত পাওয়ার কথা।', 'The maximum amount repayable under the law if a bank closes.', 2),
    (['credit rating', 'রেটিং'], 'ব্যাংক দেনা শোধ করতে পারবে কি না, সে বিষয়ে রেটিং সংস্থার মতামত; এটি আমানতের নিশ্চয়তা নয়।', 'A rating agency’s opinion of whether a bank can repay its obligations; it is not a deposit guarantee.', 2),
    (['negative outlook', 'নেতিবাচক দৃষ্টিভঙ্গি'], 'সামনে রেটিং কমতে পারে বলে সংস্থা মনে করছে।', 'The agency considers that the rating could fall.'),
    (['developing outlook', 'অনিশ্চিত পূর্বাভাস'], 'রেটিং বাড়বে না কমবে, সংস্থা এখনো নিশ্চিত নয়।', 'The agency is not yet sure whether the rating will rise or fall.'),
    (['liquidity support', 'তারল্য সহায়তা'], 'টাকার টানাটানিতে বাংলাদেশ ব্যাংক থেকে নেওয়া ধার।', 'Borrowing from Bangladesh Bank when funds are tight.'),
    (['administrator', 'প্রশাসক'], 'ব্যাংক চালাতে বাংলাদেশ ব্যাংকের নিযুক্ত ব্যক্তি।', 'A person appointed by Bangladesh Bank to run the bank.'),
    (['merger', 'resolution', 'একীভূত', 'পুনর্গঠন'], 'দুর্বল ব্যাংককে অন্য ব্যাংকের সঙ্গে মেলানো বা নতুন করে গড়া।', 'Combining a weak bank with another bank or restructuring it.'),
    (['nbfi', 'আর্থিক প্রতিষ্ঠান'], 'ব্যাংক নয়, তবে আমানত নেয় ও ঋণ দেয়।', 'A finance company that accepts deposits and makes loans, but is not a bank.'),
    (['fdr', 'এফডিআর'], 'একবারে টাকা রেখে নির্দিষ্ট সময় পর লাভসহ ফেরত।', 'A lump-sum deposit returned with profit after a set period.'),
    (['dps', 'ডিপিএস'], 'প্রতি মাসে নির্দিষ্ট টাকা জমানোর স্কিম।', 'A scheme for saving a fixed amount each month.'),
    (['savings certificate', 'সঞ্চয়পত্র'], 'সরকারের দেওয়া সঞ্চয় পণ্য।', 'A government savings product.'),
    (['mudaraba', 'মুদারাবা'], 'ইসলামী ব্যাংকের মুনাফাভিত্তিক আমানত; হার আগে থেকে নিশ্চিত নয়।', 'A profit-sharing Islamic bank deposit whose return is not guaranteed in advance.'),
    (['source tax', 'withholding tax', 'উৎসে কর'], 'লাভ দেওয়ার সময় ব্যাংক যে কর কেটে রাখে।', 'Tax deducted by the bank when paying profit.'),
    (['excise duty', 'আবগারি শুল্ক'], 'বছরে একবার জমার পরিমাণ অনুযায়ী কাটা শুল্ক।', 'An annual duty based on the deposit balance.'),
    (['inflation', 'মূল্যস্ফীতি'], 'জিনিসপত্রের দাম বছরে কত বাড়ছে।', 'The increase in the prices of goods over a year.'),
    (['real return', 'প্রকৃত মুনাফা'], 'দাম বাড়ার পর আপনার টাকার আসল বৃদ্ধি।', 'The change in purchasing power after rising prices.'),
    (['maturity', 'মেয়াদ শেষ'], 'যেদিন টাকা ফেরত পাওয়ার কথা।', 'The date on which the money is due to be returned.'),
    (['allegation', 'অভিযোগ'], 'অভিযোগ মানে এখনো প্রমাণিত নয়।', 'An allegation has not yet been proven.'),
    (['nominee', 'নমিনি'], 'আপনার অবর্তমানে যিনি টাকা পাবেন।', 'The nominated person who receives funds in your absence.'),
]


def add_glossary(db):
    from ilma_api.db import AppContent
    added = 0
    for aliases, bn, en, *revision in TERMS:
        version = revision[0] if revision else 1
        for alias in aliases:
            for language, text in [('bn', bn), ('en', en)]:
                key = 'glossary:' + alias
                if db.get(AppContent, (key, language, version)) is None:
                    db.add(AppContent(content_key=key, lang=language, version=version, text=text, status='live'))
                    added += 1
    return added
