// Trading: forecasts by Kronos on this PC, live bars and alerts from NinjaTrader, and your trade
// journal - three tabs over one pair of markets.
import { useState } from "react";
import ForecastSheet from "../forecast/ForecastSheet";
import Sheet from "../shell/Sheet";
import { Segmented } from "../ui/controls";
import Journal from "./Journal";
import Live from "./Live";

type Tab = "forecast" | "live" | "journal";

export default function TradingSheet() {
  const [tab, setTab] = useState<Tab>("forecast");
  return (
    <Sheet
      title="Trading"
      subtitle="ES and NQ: forecasts by Kronos on this PC, live alerts from NinjaTrader, and your trade journal. Not trading advice."
      width={980}
    >
      <div className="mb-4">
        <Segmented<Tab>
          id="trading-tab"
          value={tab}
          onChange={setTab}
          options={[
            { value: "forecast", label: "Forecast" },
            { value: "live", label: "Live" },
            { value: "journal", label: "Journal" },
          ]}
        />
      </div>
      {tab === "forecast" && <ForecastSheet />}
      {tab === "live" && <Live />}
      {tab === "journal" && <Journal />}
    </Sheet>
  );
}
