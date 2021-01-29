import React from 'react';
import ReactDOM from 'react-dom';
import Gui from "./Gui";
import GnbElasticClient from "./elastic/GnbElasticClient";
import Config from "./Config";

export default async function App() {
  const client: GnbElasticClient = new GnbElasticClient(Config.ES_HOST);

  const strict = true;
  await init(strict);

  function init(strict: boolean) {

    const normalJsx = <Gui client={client}/>;

    const strictJsx = <React.StrictMode>
      <Gui client={client}/>
    </React.StrictMode>;

    ReactDOM.render(
      strict ? strictJsx : normalJsx,
      document.getElementById('root')
    );

  }
}
