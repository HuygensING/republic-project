import Config from "./Config";
import React from "react";
import {VERSION} from "./Placeholder";

export default function Version() {
  return <p className="text-center small p-3">
    {VERSION}: {Config.TAG.replace('gnb-v', '')} ({Config.COMMIT.substr(0,7)})
  </p>
}
