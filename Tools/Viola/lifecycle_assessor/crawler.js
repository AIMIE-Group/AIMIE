const puppeteer = require('puppeteer-core');

const { browser } = require('./config');


class Crawler {
    constructor(config) {
        return (async () => {
            this.browser = await puppeteer.launch(config || browser);
            return this;
        }).call(this);
    }

    async close() {
        await this.browser.close();
    }
}


module.exports = { Crawler };
