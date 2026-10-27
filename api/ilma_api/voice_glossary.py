"""Authored glossary text from FRD §21.2, not model-generated financial facts."""
TERMS = [
    (['npl', 'খেলাপি ঋণ'], 'যে ঋণের টাকা সময়মতো ফেরত আসছে না।', 'Loans whose repayments are not arriving on time.'),
    (['crar', 'capital adequacy', 'মূলধন'], 'ব্যাংকের নিজের টাকা, যা ক্ষতি সামলাতে কাজে লাগে।', 'The bank’s own funds that help absorb losses.'),
    (['provision', 'প্রভিশন'], 'ক্ষতির আশঙ্কায় আগে থেকে আলাদা করে রাখা টাকা।', 'Money set aside in advance for possible losses.'),
    (['deposit insurance', 'আমানত বিমা', 'আমানত বীমা'], 'ব্যাংক বন্ধ হলে আইন অনুযায়ী যত টাকা ফেরত পাবেন।', 'The amount repayable under the law if a bank closes.'),
    (['credit rating', 'রেটিং'], 'ব্যাংকের আর্থিক শক্তির মূল্যায়ন, করে রেটিং সংস্থা।', 'A rating agency’s assessment of a bank’s financial strength.'),
    (['negative outlook', 'নেতিবাচক দৃষ্টিভঙ্গি'], 'সামনে রেটিং কমতে পারে বলে সংস্থা মনে করছে।', 'The agency considers that the rating could fall.'),
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
    for aliases, bn, en in TERMS:
        for alias in aliases:
            for language, text in [('bn', bn), ('en', en)]:
                key = 'glossary:' + alias
                if db.get(AppContent, (key, language, 1)) is None:
                    db.add(AppContent(content_key=key, lang=language, version=1, text=text, status='live'))
                    added += 1
    return added
