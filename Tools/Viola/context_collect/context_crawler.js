const puppeteer = require('puppeteer-core');
const { Crawler } = require('./crawler');
const utility = require('./utility');


class ContextCrawler extends Crawler {

    async closeAllTabs() {
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

    /**
     * @param {puppeteer.Page} tab
     */
    async tryToUpload(tab) {
        try {
            console.log(tab.url());
            await tab.waitForTimeout(1000);

            let elementHandles = await tab.$$("input[type='file']");
            console.log(elementHandles.length);

            let context_attr_block = '';
            let thresholds = [0.30, 0.34, 0.38, 0.42, 0.46];  // Collect context according to 5 density thresholds
            for await (let threshold of thresholds) {
                for await (let elementHandle of elementHandles) {
                    context_attr_block = await elementHandle.evaluate((el, threshold) => {
                        /**
                         * @param {Element} el
                         */
                        function getAttr(el) {
                            let attr = '';
                            if (el.textContent) {
                                attr += el.textContent + ' ';
                            }
                            let stack = [];
                            stack.push(el);
                            while (stack.length !== 0) {  // DFS to get all text of current html attribute
                                let el_curr = stack.pop();
                                let attr_names = el_curr.getAttributeNames();
                                for (let attr_name of attr_names) {
                                    if (attr_name === 'type' || attr_name === 'style' || attr_name === 'accept') {
                                        continue;
                                    }
                                    attr += el_curr.getAttribute(attr_name) + ' ';
                                }
                                try {
                                    let childs_obj = el_curr.children;
                                    let childs = Object.keys(childs_obj).map(function (key) { return childs_obj[key]; });
                                    for (let child of childs) {
                                        if (Object.keys(child).length === 0) {
                                            continue;
                                        }
                                        stack.push(child);
                                    }
                                } catch (error) {
                                    console.log("Children Error!");
                                }
                            }
                            return attr.replace(/\s/g, " ").replace(/ +/g, " ");
                        }

                        let density0 = 0;
                        let context_html = '';
                        let context_attr = '';
                        let lines_num = 0;
                        let words_num = 0;

                        context_html = el.outerHTML;
                        context_attr = getAttr(el);
                        lines_num = context_html.split('\n').length;
                        words_num = context_attr.split(' ').length;
                        if (words_num === 0) {
                            density0 = 0;
                        } else {
                            density0 = lines_num / words_num;
                        }

                        while (1) {  // Traverse html to collect context until the density exceeds the threshold
                            let context_attr_block = '';
                            let density = 0;
                            let previous_flag = 1;
                            let next_flag = 1;

                            // current
                            context_attr = getAttr(el);
                            context_attr_block += context_attr;

                            // previous
                            let el_p = el.previousElementSibling;
                            while (el_p) {
                                context_html = el_p.outerHTML;
                                context_attr = getAttr(el_p);
                                lines_num = context_html.split('\n').length;
                                words_num = context_attr.split(' ').length;
                                if (words_num === 0) {
                                    density = 0;
                                } else {
                                    density = lines_num / words_num;
                                }

                                if (Math.abs((density - density0)) < threshold) {
                                    context_attr_block += context_attr;
                                    if (el_p.previousElementSibling) {
                                        el_p = el_p.previousElementSibling;
                                    } else {
                                        break;
                                    }
                                } else {
                                    previous_flag = 0;
                                    break;
                                }
                            }

                            // next
                            let el_n = el.nextElementSibling;
                            while (el_n) {
                                context_html = el_n.outerHTML;
                                context_attr = getAttr(el_n);
                                lines_num = context_html.split('\n').length;
                                words_num = context_attr.split(' ').length;
                                if (words_num === 0) {
                                    density = 0;
                                } else {
                                    density = lines_num / words_num;
                                }

                                if (Math.abs((density - density0)) < threshold) {
                                    context_attr_block += context_attr;
                                    if (el_n.nextElementSibling) {
                                        el_n = el_n.nextElementSibling;
                                    } else {
                                        break;
                                    }
                                } else {
                                    next_flag = 0;
                                    break;
                                }
                            }

                            if (previous_flag === 1 && next_flag === 1 && el.parentElement && context_attr_block.length < 4096) {
                                el = el.parentElement;
                            } else {
                                if (context_attr_block.length > 2048) {
                                    return context_attr_block.substring(0, 2048);
                                } else {
                                    return context_attr_block;
                                }
                            }
                        }
                    }, threshold);

                    if (context_attr_block.replace(/\s/g, "").length > 0) {
                        break;
                    }
                    await tab.waitForTimeout(1000);
                }

                if (context_attr_block.replace(/\s/g, "").length > 0) {
                    await this.collection.insertOne({ "crawler_id": this.crawler_id, url: this.url, threshold: threshold, context: utility.strFilter(context_attr_block), time: utility.getTime() });
                }
            }
            await this.closeAllTabs();
        } catch (error) {
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
        }, 30000);

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


module.exports = { ContextCrawler };
