import { MbtistatsDashboard } from './dashboard-class.mjs';

MbtistatsDashboard.prototype.renderTopPersonality = function() {
    let topPersonality = '';
    let maxCount = 0;

    this.typeRawData.forEach(item => {
        if (item.value > maxCount) {
            maxCount = item.value;
            topPersonality = item.name;
        }
    });

    const textContainer = document.getElementById('top-personality-text');
    textContainer.textContent = `本次统计最多的人格是${topPersonality}`;

    const imageContainer = document.getElementById('top-personality-image');
    const img = new Image();
    img.src = `../images/${topPersonality}.png`;
    img.alt = `${topPersonality}人格图片`;

    img.onload = function () {
        imageContainer.innerHTML = '';
        imageContainer.appendChild(img);
    };

    img.onerror = function () {
        imageContainer.innerHTML = '<div class="purple-placeholder"></div>';
    };
};