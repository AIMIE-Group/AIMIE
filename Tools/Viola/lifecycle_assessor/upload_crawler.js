const puppeteer = require('puppeteer-core');
const request = require('request');
const crypto = require('crypto');
const fs = require('fs');
const util = require('util');
const stream = require('stream');
const pipeline = util.promisify(stream.pipeline);
const bh = require('blockhash');
const jpeg = require('jpeg-js');
const { execSync } = require('child_process');

const { Crawler } = require('./crawler');
const utility = require('./utility');

const keywords = require('./keywords.json');
require('events').EventEmitter.defaultMaxListeners = 20;

const comPattern = /https?:[^\s"']+?.jpe?g[^\s"']*/ig;
const spePattern = /https?:[^\s"']+?[a-z0-9-]{13,}[^\s"']*/ig;


class UploadCrawler extends Crawler {

    async closeAllTabs() {
        console.log('\ncloseAllTabs!');
        while (1) {
            if ((await this.browser.pages()).length <= 1) {
                break;
            }
            await (await this.browser.pages())[1].close();
        }
    }

    /**
     * @param {puppeteer.Page} tab
     */
    async setTab(tab) {
        try {
            // callbacks
            tab.on('dialog', async (dialog) => {
                try {
                    await dialog.accept();
                } catch (error) {
                    console.log('\tdialog Error!');
                }
            });
        } catch (error) {
            console.log("setTab Error!");
            throw "setTab Error!";
        }
    }

    excludeNoise(link) {
        for (let exclude of keywords.link.exclude) {
            if (link.includes(exclude)) {
                return false;
            }
        }
        return true;
    }

    async linkMatch(string, from) {
        let comlinks = string.match(comPattern);
        if (comlinks) {
            for await (let comlink of comlinks) {
                if (this.excludeNoise(comlink)) {
                    comlink = comlink.replace(/\\/ig, '');
                    await this.picFilter(comlink, from);
                }
            }
        }
        let spelinks = string.match(spePattern);
        if (spelinks) {
            for await (let spelink of spelinks) {
                if (this.excludeNoise(spelink)) {
                    spelink = spelink.replace(/\\/ig, '');
                    await this.picFilter(spelink, from);
                }
            }
        }
    }

    async stageRecord(from) {
        if (from === 0) {
            if (this.stage === 0) {
                this.stage_flags[0] = 1;
            } else {
                this.stage_flags[3] = 1;
            }
        } else {
            if (this.stage === 0) {
                this.stage_flags[1] = 1;
            } else {
                this.stage_flags[2] = 1;
            }
        }
    }

    async picFilter(link, from) {
        try {
            const hash = crypto.createHash('md5');
            let buffer = request(link);
            await pipeline(
                buffer,
                hash
            );
            let md5 = hash.digest('hex');

            if (md5 === 'dc0cac8c72f1a17866c9f3fde9a3ec9f') {
                await this.stageRecord(from);

                this.pic_link = link;
                this.pic_modified = 0;
            }
            else if (this.pic_modified !== 0) {
                buffer = request(link);
                let jpg_path = `./pic_cache/${this.crawler_id}-${utility.getMs()}.jpg`;
                let write_stream = fs.createWriteStream(jpg_path);
                await pipeline(
                    buffer,
                    write_stream
                );
                buffer = fs.readFileSync(jpg_path);
                let jpg_hash = bh.blockhashData(jpeg.decode(buffer), 16, 2);
                let origin_hash = 'fe7fce63c003c003f20ff40fe00fe007e007e00ff00ff81fc001cc11fc1bfc3f';
                let similarity = bh.hammingDistance(origin_hash, jpg_hash);
                if (similarity < 32) {
                    await this.stageRecord(from);

                    this.pic_link = link;
                    this.pic_modified = 1;
                }
            }
        } catch (error) {
            console.log('picFilter Error!');
        }
    }

    /**
     * @param {puppeteer.Page} tab
     */
    async setListener(tab) {
        try {
            // callbacks
            tab.on('request', async request => {
                let url = request.url();
                if ((comPattern.test(url) || spePattern.test(url)) && this.excludeNoise(url)) {  // Filter pic link in URL
                    await this.picFilter(url, 0);
                }

                if (request.method() === 'POST' || request.method() === 'PUT') {  // Filter pic link in POST/PUT
                    let postData = request.postData();
                    try {
                        await this.linkMatch(postData, 1);
                    } catch {
                        console.log('\tpostData Error!');
                    }

                    if (postData === undefined || postData.length > 5120) {
                        if (this.excludeNoise(url)) {
                            this.has_api = 1;
                            this.upload_api = url;
                        }
                    }
                }
            });

            tab.on('response', async (response) => {  // Filter pic link in response
                try {
                    const headers = JSON.stringify(response.headers());
                    await this.linkMatch(headers, 1);

                    await response.text().then(async (body) => {
                        try {
                            if (body.length < 5120) {
                                await this.linkMatch(body, 1);
                            }
                        } catch (error) {
                            console.log("\tresponse.text Error!");
                        }
                    });
                } catch (error) {
                    console.log("\tresponse Error!");
                }
            });
        } catch (error) {
            console.log("setListener Error!");
        }
    }

    /**
     * @param {puppeteer.Page} tab
     * @returns {puppeteer.ElementHandle<Element>[]}
     */
    async getElements(tab, xpath) {
        const elements = await Promise.all(
            xpath.map(i => tab.$x(i))
        );
        if (elements.filter(item => item.length > 0).length === 0) {
            return [];
        }
        return Array.from(new Set(elements.reduce((i, j) => i.concat(j))));
    }

    /**
     * @param {puppeteer.Page} tab
     * @returns {puppeteer.ElementHandle<Element>[]}
     */
    async typeText(tab) {
        let radioEleHans = (await tab.$$("input[type='radio']")).concat(await tab.$$("span[class='checkmark']"));
        for await (let radioEleHan of radioEleHans) {
            try {
                await radioEleHan.click();
                await tab.waitForTimeout(500);
            } catch (error) {
                console.log("\tradioEleHan Error!");
            }
        }

        let checkBoxEleHans = await tab.$$("input[type='checkbox']");
        for await (let checkBoxEleHan of checkBoxEleHans) {
            try {
                await checkBoxEleHan.click();
                await tab.waitForTimeout(500);
            } catch (error) {
                console.log("\tradioEleHan Error!");
            }
        }

        let textEleHans = (await tab.$$("input[type='text']")).concat(await tab.$$("textarea")).concat(await tab.$$("input[type='email']"));
        for await (let textEleHan of textEleHans) {
            try {
                await textEleHan.click({ clickCount: 3 });

                let text = (await textEleHan.evaluate(el => el.outerHTML)).toLowerCase();
                if (text.includes("select")) {
                    continue;
                }

                if (text.includes("detail") || text.includes("issue") || text.includes("describe") || text.includes("search") || text.includes("详情") || text.includes("描述")) {
                    await textEleHan.type("Detecting picture storage abuse.", { delay: 20 });
                } else if (text.includes("标题")) {
                    await textEleHan.type("DetectAbuse", { delay: 20 });
                } else if (text.includes("email")) {
                    await textEleHan.type("123456789@gmail.com", { delay: 20 });
                } else if (text.includes("name")) {
                    await textEleHan.type("TomCruise", { delay: 20 });
                } else if (text.includes("姓") || text.includes("名")) {
                    await textEleHan.type("司徒", { delay: 20 });
                } else if (text.includes("age") || text.includes("年龄")) {
                    await textEleHan.type("28", { delay: 20 });
                } else if (text.includes("phone") || text.includes("联系方式") || text.includes("电话")) {
                    await textEleHan.type("1324567890", { delay: 20 });
                } else {
                    await textEleHan.type("DetectAbuse", { delay: 20 });
                }
                await tab.waitForTimeout(500);
            } catch (error) {
                console.log("\ttextEleHans Error!");
            }
        }
    }

    /**
     * @param {puppeteer.Page} tab
     */
    async tryToUpload(tab) {
        try {
            console.log(tab.url());
            await tab.waitForTimeout(1000);

            this.stage_flags = [0, 0, 0, 0]  // [preview, presubmit, submit, callback]
            this.stage = 0;

            let elementHandles = await tab.$$("input[type='file']");
            console.log(elementHandles.length);
            if (elementHandles.length !== 0) {
                this.pic_link = '';
                this.pic_modified = -1;  // 0-origin 1-modified
                this.has_api = 0;
                this.upload_api = '';

                await this.setListener(tab);
                for await (let elementHandle of elementHandles) {
                    try {
                        await elementHandle.uploadFile('./AAAA.jpg');  // Upload process before clicking the submit button
                        await tab.waitForTimeout(1000);
                    } catch (error) {
                        console.log("\tuploadFile Error!");
                    }
                }
                await tab.waitForTimeout(15000);

                await this.typeText(tab);

                let submits = (await this.getElements(tab, keywords.submit)).concat(await tab.$$("input[type='submit']"));
                console.log("\tsubmit Buttons: " + submits.length);
                if (submits.length !== 0) {
                    this.stage = 1;

                    for await (let submit of submits) {  // Upload process after clicking the submit button
                        try {
                            await tab.keyboard.down('Control');
                            await submit.click();
                            await tab.keyboard.up('Control');
                            await tab.waitForTimeout(500);

                            await tab.keyboard.down('Control');
                            await submit.click();
                            await tab.keyboard.up('Control');
                            await tab.waitForTimeout(500);
                        } catch (error) {
                            console.log("\tsubmit Error!");
                        }
                    }
                    await tab.waitForTimeout(15000);
                }

                if (this.pic_link !== '') {
                    console.log(this.pic_link);
                    await this.collection.updateOne({ "crawler_id": this.crawler_id }, { '$set': { source: source, url: this.url, has_pic: 1, pic_link: this.pic_link, pic_modified: this.pic_modified, has_api: this.has_api, upload_api: this.upload_api, stage_flags: this.stage_flags, time: utility.getTime() } }, { upsert: true });
                }
                else {
                    await this.collection.updateOne({ "crawler_id": this.crawler_id }, { '$set': { source: source, url: this.url, has_pic: -1, pic_link: '', pic_modified: 0, has_api: this.has_api, upload_api: this.upload_api, stage_flags: this.stage_flags, time: utility.getTime() } }, { upsert: true });
                }
            }
            else {
                await this.collection.updateOne({ "crawler_id": this.crawler_id }, { '$set': { source: source, url: this.url, has_pic: -2, pic_link: '', pic_modified: 0, has_api: 0, upload_api: '', stage_flags: this.stage_flags, time: utility.getTime() } }, { upsert: true });
            }

            execSync(`rm -f ./pic_cache/${this.crawler_id}*`);
            await tab.waitForTimeout(1000);
            await this.closeAllTabs();
        } catch (error) {
            execSync(`rm -f ./pic_cache/${this.crawler_id}*`);
            console.log("\ttryToUpload Error!");
            console.log(error);
            throw "tryToUpload Error!";
        }
    }

    async newCrawlerTabs() {
        console.log(`${this.crawler_id}: ${this.url}`);
        console.log('uptime: ' + process.uptime());

        const internal = setInterval(async () => {
            try {
                console.log(`\n${this.crawler_id}: Interval`);
                if ((await this.browser.pages()).length > 1) {
                    let currentTab = (await this.browser.pages())[1];
                    if (this.currentURL == currentTab.url()) {
                        clearInterval(internal);
                        console.log(`Close Browser: ${this.currentURL}`);
                        await this.browser.close();
                    }
                    this.currentURL = currentTab.url();
                }
            } catch (error) {
                console.log('setInterval Error!');
                clearInterval(internal);
                console.log(`Close Browser: ${this.currentURL}`);
                await this.browser.close();
            }
        }, 60000);

        try {
            const rootTab = await this.browser.newPage();
            await this.setTab(rootTab);
            await rootTab.waitForTimeout(1000);

            try {
                await rootTab.goto(this.url, { waitUntil: 'domcontentloaded' });
            } catch (error) {
                console.log("Navigation Timeout! Continue...");
            }
            if (rootTab.url() === 'about:blank' || rootTab.url() === 'chrome-error://chromewebdata/') {
                console.log("rootTab: " + rootTab.url());
                await rootTab.close();
                clearInterval(internal);
                return;
            }
            await rootTab.waitForTimeout(5000);

            await this.tryToUpload(rootTab);

            clearInterval(internal);
            console.log(`${this.crawler_id} Success`);
        } catch (error) {
            clearInterval(internal);
            console.log(`${this.crawler_id} Error!`);
            throw 'New Browser!';
        }
    }
}


module.exports = { UploadCrawler };
