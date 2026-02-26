import { MbtistatsDashboard } from './dashboard-class.mjs';

MbtistatsDashboard.prototype.renderTopPersonality = function() {
    // 找到最大值及所有并列第一的人格
    let maxCount = 0;
    const topPersonalities = [];
    this.typeRawData.forEach(item => {
        if (item.value > maxCount) {
            maxCount = item.value;
            topPersonalities.length = 0;
            topPersonalities.push(item.name);
        } else if (item.value === maxCount && item.value > 0) {
            topPersonalities.push(item.name);
        }
    });

    // 文字部分
    const textContainer = document.getElementById('top-personality-text');
    if (topPersonalities.length === 0) {
        textContainer.textContent = '暂无统计数据';
    } else if (topPersonalities.length === 1) {
        textContainer.textContent = `本次统计最多的人格是${topPersonalities[0]}`;
    } else {
        textContainer.textContent = `本次统计最多的类型是${topPersonalities.join('、')}`;
    }

    // 图片部分
    const imageContainer = document.getElementById('top-personality-image');
    imageContainer.innerHTML = '';

    if (topPersonalities.length === 0) {
        imageContainer.innerHTML = '<div class="purple-placeholder"></div>';
        return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = `top-personality-wrapper top-personality-count-${topPersonalities.length}`;

    // 计算行数：超过3个分两行，否则单行
    const rowCount = topPersonalities.length > 3 ? 2 : 1;
    const itemsPerRow = Math.ceil(topPersonalities.length / rowCount);

    for (let i = 0; i < rowCount; i++) {
        const rowItems = topPersonalities.slice(i * itemsPerRow, (i + 1) * itemsPerRow);
        wrapper.appendChild(createRow(rowItems, this.colorMap));
    }

    imageContainer.appendChild(wrapper);
};

function createRow(types, colorMap) {
    const row = document.createElement('div');
    row.className = 'top-personality-row';
    types.forEach(type => {
        row.appendChild(createImageElement(type, colorMap[type] || '#cccccc'));
    });
    return row;
}

function createImageElement(type, color) {
    const img = document.createElement('img');
    img.src = `../images/${type}.png`;
    img.alt = `${type}人格图片`;
    img.className = 'top-personality-img';
    img.onerror = function() {
        this.style.display = 'none';
        const placeholder = document.createElement('div');
        placeholder.className = 'type-placeholder';
        placeholder.style.backgroundColor = color;
        placeholder.textContent = type;
        this.parentNode.appendChild(placeholder);
    };

    const container = document.createElement('div');
    container.className = 'top-personality-item';
    container.appendChild(img);
    return container;
}
