// Explicitly opted-in acceptance recordings; never uploads audio or stores names.
const prompts = [
  ['EBL', 'ইস্টার্ন ব্যাংক', 'bn', 'bank'], ['BRAC', 'ব্র্যাক ব্যাংক', 'bn', 'bank'],
  ['City', 'সিটি ব্যাংক', 'bn', 'bank'], ['MTB', 'এমটিবি ব্যাংক', 'bn', 'bank'],
  ['NCC', 'এনসিসি ব্যাংক', 'bn', 'bank'], ['Prime', 'প্রাইম ব্যাংক', 'bn', 'bank'],
  ['DBBL', 'ডাচ বাংলা ব্যাংক', 'bn', 'bank'], ['Bank Asia', 'ব্যাংক এশিয়া', 'bn', 'bank'],
  ['SBAC', 'এসবিএসি ব্যাংক', 'bn', 'bank'],
  ['EBL', 'ইস্টার্ন ব্যাংকের খেলাপি ঋণ কত?', 'bn', 'question'],
  ['BRAC', 'ব্র্যাক ব্যাংকের এফডিআর রেট কত?', 'bn', 'question'],
  ['City', 'Is City Bank safe?', 'en', 'question'],
  ['DBBL', 'What is Dutch Bangla Bank’s credit rating?', 'en', 'question'],
  ['MTB', 'এমটিবি ব্যাংকের অবস্থা কেমন?', 'bn', 'question']
];
const element = id => document.getElementById(id);
const rows = [];
let recorder = null, pending = null, finishing = false, active = null;
const select = element('capture-choice');
prompts.forEach((prompt, index) => { const option = document.createElement('option'); option.value = index; option.textContent = prompt[1]; select.appendChild(option); });
select.onchange = () => { element('capture-prompt').textContent = prompts[Number(select.value)][1]; };
select.onchange();
function say(text) { element('capture-status').textContent = text; }
function download(blob, filename) {
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function finish() {
  if (!recorder || finishing) return;
  finishing = true; element('capture-stop').disabled = true;
  try {
    const audio = await recorder.finish();
    const extension = audio.type.includes('mp4') ? 'mp4' : 'webm';
    const file = `real-${String(rows.length + 1).padStart(3, '0')}-${active.role}-${active.condition}.${extension}`;
    pending = { audio, file, ...active }; element('capture-download').disabled = false;
    say('Ready to download. Download this recording before starting another.');
  } catch { say('Could not record. Please try again.'); element('capture-start').disabled = false; }
  finally { recorder = null; finishing = false; }
}
element('capture-start').onclick = async () => {
  if (!window.IlmaVoiceRecorder.supported() || !window.isSecureContext) { say('Open this page over HTTPS in a browser that supports microphone recording.'); return; }
  element('capture-start').disabled = true;
  active = { role: element('capture-role').value, condition: element('capture-condition').value, prompt: prompts[Number(select.value)] };
  recorder = new window.IlmaVoiceRecorder();
  try {
    await recorder.start({ silenceMs: Number(element('capture-silence').value), onComplete: finish,
      onError: () => { recorder?.cancel(); recorder = null; say('No speech heard. Try again.'); element('capture-start').disabled = false; element('capture-stop').disabled = true; } });
    say('Recording. Say the displayed prompt.'); element('capture-stop').disabled = false;
  } catch { recorder?.cancel(); recorder = null; say('Microphone unavailable. Check browser permission.'); element('capture-start').disabled = false; }
};
element('capture-stop').onclick = finish;
element('capture-download').onclick = () => {
  if (!pending) return;
  download(pending.audio, pending.file);
  rows.push([pending.file, pending.prompt[0], pending.prompt[2], 'bn', pending.role, pending.condition, 'home', pending.prompt[3]]);
  pending = null; element('capture-download').disabled = true; element('capture-start').disabled = false; element('capture-csv').disabled = false;
  element('capture-count').textContent = `${rows.length} recordings saved`; say('Recording downloaded. Choose the next prompt.');
};
element('capture-csv').onclick = () => {
  const quote = value => '"' + String(value).replaceAll('"', '""') + '"';
  download(new Blob(['file,bank,language,ui_lang,speaker_role,condition,tab,test_kind\n' + rows.map(row => row.map(quote).join(',')).join('\n')], { type: 'text/csv' }), 'references_real.csv');
};
window.addEventListener('pagehide', () => { recorder?.cancel(); pending = null; });
