<script lang="ts">
  import HoldingsPreview from "../dashboard/HoldingsPreview.svelte";
  import type { HoldingsLiveReportProps } from "./index.ts";

  let { holdings, commodities }: HoldingsLiveReportProps = $props();
</script>

<HoldingsPreview {holdings} {commodities} />
