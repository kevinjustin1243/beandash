<script lang="ts">
  import HoldingsPreview from "../dashboard/HoldingsPreview.svelte";
  import type { HoldingsLiveReportProps } from "./index.ts";

  let { holdingsReport, commodities }: HoldingsLiveReportProps = $props();
</script>

<HoldingsPreview {holdingsReport} {commodities} />
