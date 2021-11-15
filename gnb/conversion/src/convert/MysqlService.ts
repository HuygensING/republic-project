import * as mysql from 'mysql';
import Config from "../Config";

export default class MysqlService {

  private connection: mysql.Connection;

  public async connect() {
    this.connection = await mysql.createConnection(Config.MYSQL_CONNECTION);
    await this.connection.connect();
  }

  public async getAllPeople(): Promise<any> {
    return new Promise(
      (resolve, reject) => {
        return this.connection.query('select * from personen_met_categorie', function (error, results, fields) {
          if (error) reject(error);
          resolve(results);
        })
      }
    );
  }

  public async getAllFunctions(): Promise<any> {
    return new Promise(
      (resolve, reject) => {
        const query = 'select ' +
          '  persoon, functienaam as naamId, fn.naam as naam, ' +
          '  beginJaar, beginMaand, beginDag, ' +
          '  eindJaar, eindMaand, eindDag, ' +
          '  functietype ' +
          'from functie as f ' +
          '  left join fn as fn' +
          '  on f.functienaam = fn.ID_functienaam ' +
          'where fn.ID_functienaam is not null ' +
          ';';

        return this.connection.query(query, function (error, results, fields) {
          if (error) reject(error);
          resolve(results);
        })
      }
    );
  }

  public close() {
    console.log('Close connection')
    this.connection.end();
  }

}
