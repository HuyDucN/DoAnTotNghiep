const analysisButton = document.getElementById('run-analysis');
const scoreMatch = document.getElementById('score-match');
const skillMatch = document.getElementById('skill-match');
const skillGap = document.getElementById('skill-gap');
const matchedSkills = document.getElementById('matched-skills');
const missingSkills = document.getElementById('missing-skills');
const recommendations = document.getElementById('recommendations');
const topbarLabel = document.getElementById('topbar-label');
const topbarTitle = document.getElementById('topbar-title');

const knownSkills = [
  { name: 'Python', level: 92 },
  { name: 'SQL', level: 88 },
  { name: 'Machine Learning', level: 80 },
  { name: 'Data Analysis', level: 85 },
  { name: 'Git', level: 75 },
  { name: 'NLP', level: 68 }
];

const missingList = ['Docker', 'Cloud Deployment', 'NLP nâng cao'];
const recList = [
  'Hoàn thiện Docker và CI/CD cho dự án AI.',
  'Rèn thêm kỹ năng NLP và mô hình hóa dữ liệu.',
  'Tham gia khóa học về Azure / Cloud AI.'
];

const viewMap = {
  dashboard: { label: 'Overview', title: 'Dashboard tổng quan' },
  analysis: { label: 'Candidate', title: 'Phân tích CV & kỹ năng' },
  skills: { label: 'Skills', title: 'Skill Matrix' },
  reports: { label: 'Reports', title: 'Báo cáo hiệu suất' },
  settings: { label: 'Settings', title: 'Cài đặt AI' }
};

function renderSkills(list, container) {
  container.innerHTML = '';
  list.forEach((item) => {
    const li = document.createElement('li');
    const label = document.createElement('span');
    label.textContent = item.name;

    const progress = document.createElement('div');
    progress.className = 'progress';

    const fill = document.createElement('i');
    fill.style.width = `${item.level}%`;
    progress.appendChild(fill);

    li.appendChild(label);
    li.appendChild(progress);
    container.appendChild(li);
  });
}

function renderMissing(list, container) {
  container.innerHTML = '';
  list.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    container.appendChild(li);
  });
}

function renderRecommendations(list, container) {
  container.innerHTML = '';
  list.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    container.appendChild(li);
  });
}

function setActiveView(view) {
  const panels = document.querySelectorAll('.view-panel');
  panels.forEach((panel) => panel.classList.toggle('active', panel.id === view));

  const buttons = document.querySelectorAll('.nav-item');
  buttons.forEach((button) => button.classList.toggle('active', button.dataset.view === view));

  const info = viewMap[view] || viewMap.dashboard;
  topbarLabel.textContent = info.label;
  topbarTitle.textContent = info.title;
}

analysisButton.addEventListener('click', () => {
  const cvValue = document.getElementById('cv-upload').files?.[0]?.name || 'CV.pdf';
  const jobText = document.getElementById('job-desc').value.toLowerCase();

  let detected = 0;
  const skillFound = knownSkills.filter((item) => {
    const normalized = item.name.toLowerCase().replace(/\s+/g, '');
    if (jobText.includes(normalized)) {
      detected += 1;
      return true;
    }
    return false;
  });

  const score = Math.min(92, Math.max(68, 65 + detected * 6));
  const matchedCount = Math.min(skillFound.length + 1, 6);
  const gapCount = Math.max(2, 9 - matchedCount);

  scoreMatch.textContent = `${Math.round(score)}%`;
  skillMatch.textContent = `${matchedCount}/9`;
  skillGap.textContent = `${gapCount}`;

  renderSkills(knownSkills, matchedSkills);
  renderMissing(missingList, missingSkills);
  renderRecommendations(recList, recommendations);

  const successPill = document.querySelector('.pill.success');
  if (successPill) successPill.textContent = `${Math.round(score)}% phù hợp`;

  const uploadPill = document.querySelector('.upload-panel .panel-header .pill');
  if (uploadPill) uploadPill.textContent = cvValue;
});

const navButtons = document.querySelectorAll('.nav-item');
navButtons.forEach((button) => {
  button.addEventListener('click', () => setActiveView(button.dataset.view));
});

renderSkills(knownSkills, matchedSkills);
renderMissing(missingList, missingSkills);
renderRecommendations(recList, recommendations);
setActiveView('dashboard');
