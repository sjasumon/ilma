"""Handwritten number, acronym and display/TTS separation cases."""
from ilma_api.voice_numbers import bangla_number,pronounce
import pytest,re

@pytest.mark.parametrize('value,expected',[(0,'শূন্য'),(9,'নয়'),(18,'আঠারো'),(7750,'সাত হাজার সাতশো পঞ্চাশ'),(89040000000,'আট হাজার নয়শো চার কোটি'),(99999999,'নয় কোটি নিরানব্বই লাখ নিরানব্বই হাজার নয়শো নিরানব্বই'),('12.5','সাড়ে বারো'),('7.75','পৌনে আট'),('7.25','সোয়া সাত'),('7.8','সাত দশমিক আট'),('-5.5','মাইনাস সাড়ে পাঁচ')])
def test_lakh_crore_and_fraction_words(value,expected):assert bangla_number(value)==expected

def test_ratio_rounding_is_explicit_not_applied_to_exact_service_prices():
    assert bangla_number('18.07',ratio=True)=='আঠারো'
    assert bangla_number('-5.48',ratio=True)=='মাইনাস সাড়ে পাঁচ'
    assert pronounce('৭.৭৫%', 'bn')=='পৌনে আট শতাংশ'
    assert pronounce('-৫.৪৮%', 'bn')=='মাইনাস সাড়ে পাঁচ শতাংশ'


def test_tts_normalization_leaves_display_unchanged_and_is_idempotent():
    display='CRAB AAA · ২০২৫ সাল; FDR ৭.৭৫% (২,০০,০০০ টাকা), ৮৯০ কোটি। BRAC DBBL NCC MTB SBAC ECRL CRISL'
    spoken=pronounce(display,'bn')
    assert not re.search(r'[0-9০-৯%()·—;A-Za-z]',spoken)
    assert 'ট্রিপল এ' in spoken and 'দুই লাখ টাকা' in spoken
    assert 'দুই হাজার পঁচিশ সাল' in spoken and 'আটশো নব্বই কোটি' in spoken
    assert 'ক্র্যাব' in spoken and 'পৌনে আট শতাংশ' in spoken
    assert pronounce(spoken,'bn')==spoken
    assert '৭.৭৫%' in display
    assert pronounce('AAA earns 7.75% on Tk 100000.','en')=='triple A earns 7.75 percent on 100000 taka.'


def test_small_negative_percentages_never_become_zero():
    assert pronounce('-০.০৪%','bn')=='মাইনাস শূন্য দশমিক শূন্য চার শতাংশ'
    assert bangla_number('.5')=='অর্ধেক'
    assert bangla_number('.25')=='শূন্য দশমিক দুই পাঁচ'
