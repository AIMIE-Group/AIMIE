const mysql = require('mysql2/promise');
const Redis = require("ioredis");
const { MongoClient } = require("mongodb");
const config = require('./config');


class DB {
    constructor() {
        return (async () => {
            // mongo
            this.mongo = new MongoClient(config.mongo.uri, { useUnifiedTopology: true });
            await this.mongo.connect();
            this.mongoDatabase = this.mongo.db(config.mongo.db);
            // mysql
            this.mysql = mysql.createPool(config.mysql);
            // redis
            this.redis = new Redis(config.redis);

            return this;
        }).call(this);
    }

    async select(sql, args) {
        try {
            const [row] = await this.mysql.query(sql, args);
            return row;
        } catch (err) {
            console.error(err);
            return [];
        }
    }

    async update(sql, args) {
        try {
            await this.mysql.execute(sql, args);
        } catch (err) {
            console.error(err);
        }
    }

    async fetchFromRedis(key, num) {
        const rows = [];
        for (let i = 0; i < num; i++) {
            const item = await this.redis.lpop(key);
            if (item !== null) {
                rows.push(JSON.parse(item));
            } else {
                break;
            }
        }
        return rows;
    }

    async addToRedis(key, rows) {
        for (let row of rows) {
            await this.redis.lpush(key, JSON.stringify(row));
        }
    }

    async updateMongo(collection, filter, update) {
        await collection.updateOne(filter, update);
    }

    async close() {
        await this.mongo.close();
        await this.mysql.end();
        this.redis.disconnect();
    }
}


module.exports = { DB };
