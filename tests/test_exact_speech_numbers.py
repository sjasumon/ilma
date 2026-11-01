"""Synthetic exact-value speech cases; never round audited numbers for narration."""
import pytest
from ilma_api.exact_speech_numbers import prepare,number_words
@pytest.mark.parametrize('token,expected',[
 ('7.25','সাত দশমিক দুই পাঁচ'),('15.63','পনেরো দশমিক ছয় তিন'),('2.03','দুই দশমিক শূন্য তিন'),('2,121','দুই হাজার একশো একুশ'),('1500','এক হাজার পাঁচশো'),('10000','দশ হাজার'),('20000','বিশ হাজার'),('2001','দুই হাজার এক'),('-5.48','মাইনাস পাঁচ দশমিক চার আট'),('0.04','শূন্য দশমিক শূন্য চার')])
def test_bangla_exact_numbers(token,expected):assert number_words(token,'bn')==expected

def test_precision_and_display_are_preserved():
    display='নমুনা হার -৫.৪৮%, ২.০৩%, ৭.২৫%; ২,১২১ কোটি টাকা।'
    speech,spans=prepare(display,'bn')
    assert [s['value'] for s in spans]==['-5.48','2.03','7.25','2121']
    assert 'মাইনাস পাঁচ দশমিক চার আট শতাংশ' in speech
    assert 'শূন্য তিন শতাংশ' in speech and '৭.২৫%' in display
    assert prepare(speech,'bn')[0]==speech

def test_lists_and_ranges_do_not_turn_into_amounts_or_negatives():
    text,spans=prepare('১, ২ বা ৩ বছরে; ৫-৯ বছর; ২,০০,০০০ টাকা','bn')
    assert [s['value'] for s in spans]==['1','2','3','5','9','200000']
    assert 'এক, দুই বা তিন' in text and 'পাঁচ থেকে নয়' in text and 'দুই লাখ' in text

def test_english_exact_decimals_and_money():
    text,spans=prepare('Sample 15.63%, 2,121 crore and Tk 10000.','en')
    assert 'fifteen point six three percent' in text and 'two thousand one hundred twenty-one crore' in text
    assert 'ten thousand taka' in text and [s['value'] for s in spans]==['15.63','2121','10000']
