import React from 'react';
import ReactDOM from 'react-dom';
import Gui from "./Gui";
import GnbElasticClient from "./elastic/GnbElasticClient";
import Config from "./Config";
import ErrorBoundary from "./error/ErrorBoundary";

export default async function App() {

  const client: GnbElasticClient = new GnbElasticClient(Config.ES_HOST);

  const strict = false;
  await init(strict);

  function init(strict: boolean) {
    const normalJsx = <Gui client={client}/>;

    const strictJsx = <React.StrictMode>
      <Gui client={client}/>
    </React.StrictMode>;

    ReactDOM.render(
      <>
        <ErrorBoundary>
          {strict ? strictJsx : normalJsx}
        </ErrorBoundary>
      </>,
      document.getElementById('root')
    );

  }
}
