const puppeteer = require('puppeteer-core');
const { browser } = require('./config');
const { UploadCrawler } = require('./upload_crawler');
const { DB } = require('./db');
const utility = require('./utility');

require('events').EventEmitter.defaultMaxListeners = 20;


(async () => {
    const db = await new DB();
    const crawler = await new UploadCrawler();
    crawler.db = db;
    crawler.collection = await db.mongoDatabase.collection('img_crawler');
    crawler.currentURL = '';

    const input_collection = await db.mongoDatabase.collection('input_collection');
    let from = 0;
    const batch_size = 1000;
    while (1) {
        let inputs = await input_collection.find().skip(from).limit(batch_size).toArray();
        if (inputs.length === 0) {
            await utility.sleep(600000);
            continue;
        }
        for await (let input of inputs) {
            let url = input.url;
            let crawler_id = input.crawler_id;
            if (!url.startsWith('http')) {
                url = 'https://' + url;
            }
            let idExist = await crawler.collection.find({ "crawler_id": crawler_id }).count();
            let urlExist = await crawler.collection.find({ "url": url }).count();
            if (idExist === 0 && urlExist === 0) {
                try {
                    crawler.url = url;
                    crawler.crawler_id = crawler_id;
                    await crawler.newCrawlerTabs();
                } catch (error) {  // restart crawler
                    console.log(error);
                    await crawler.browser.close();
                    console.log('\nNew Browser...');
                    crawler.browser = await puppeteer.launch(browser);
                }
            }
        }
        from += inputs.length;
    }

    await crawler.close();
    process.exit(0);
})();
