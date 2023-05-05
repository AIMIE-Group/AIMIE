function getTime() {
    let date = new Date();
    function add0(x) {
        return x < 10 ? '0' + x : x;
    }
    return `${date.getFullYear()}-${add0(date.getMonth() + 1)}-${add0(date.getDate())} ${add0(date.getHours())}:${add0(date.getMinutes())}:${add0(date.getSeconds())}`;
}


function getMs() {
    let date = new Date();
    return date.getMilliseconds();
}


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}


module.exports = {
    getTime,
    getMs,
    sleep
};
