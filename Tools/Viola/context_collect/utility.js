const keywords = require('./keywords.json');


function getTime() {
    let date = new Date();
    function add0(x) {
        return x < 10 ? '0' + x : x;
    }
    return `${date.getFullYear()}-${add0(date.getMonth() + 1)}-${add0(date.getDate())} ${add0(date.getHours())}:${add0(date.getMinutes())}:${add0(date.getSeconds())}`;
}


function strFilter(str) {
    let str_filtered = str.toLowerCase().replace(/[0-9!"#$%&\'()*+,\-./:;<=>?@[\]^_`{|}~～–…—：、，；【】｜¥·。？！（）《〈〉》‘’“”×]/g, " ");
    str_filtered = str_filtered.replace(/[\t\n\r]/g, " ").replace(/ +/g, " ");

    let words = str_filtered.split(' ');
    let stopwords = keywords.stopwords;
    words = words.filter(function (word) {
        return !stopwords.includes(word);
    });
    str_filtered = words.join(' ');

    return str_filtered;
}


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}


module.exports = {
    getTime,
    strFilter,
    sleep
};
