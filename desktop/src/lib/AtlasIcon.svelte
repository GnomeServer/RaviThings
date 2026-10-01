<script module lang="ts">
  export type IconName = "mission" | "research" | "archive" | "activity" | "settings" | "search" | "close" | "chevron-down" | "chevron-right" | "arrow-right" | "copy" | "alert" | "check" | "eye" | "pause" | "play" | "trash" | "source";
</script>

<script lang="ts">
  import mission from "./vendor/sirocco/icons/mission.svg?raw";
  import research from "./vendor/sirocco/icons/research.svg?raw";
  import archive from "./vendor/sirocco/icons/archive.svg?raw";
  import activity from "./vendor/sirocco/icons/activity.svg?raw";
  import settings from "./vendor/sirocco/icons/settings.svg?raw";
  import search from "./vendor/sirocco/icons/search.svg?raw";
  import close from "./vendor/sirocco/icons/close.svg?raw";
  import chevronDown from "./vendor/sirocco/icons/chevron-down.svg?raw";
  import chevronRight from "./vendor/sirocco/icons/chevron-right.svg?raw";
  import arrowRight from "./vendor/sirocco/icons/arrow-right.svg?raw";
  import copy from "./vendor/sirocco/icons/copy.svg?raw";
  import alert from "./vendor/sirocco/icons/alert.svg?raw";
  import check from "./vendor/sirocco/icons/check.svg?raw";
  import eye from "./vendor/sirocco/icons/eye.svg?raw";
  import pause from "./vendor/sirocco/icons/pause.svg?raw";
  import play from "./vendor/sirocco/icons/play.svg?raw";
  import trash from "./vendor/sirocco/icons/trash.svg?raw";
  import source from "./vendor/sirocco/icons/source.svg?raw";

  let { name, class: iconClass }: { name: IconName; class?: "sc-rail__icon" | "sc-notice__icon" } = $props();
  const icons: Record<IconName, string> = { mission, research, archive, activity, settings, search, close, "chevron-down": chevronDown, "chevron-right": chevronRight, "arrow-right": arrowRight, copy, alert, check, eye, pause, play, trash, source };
  const markup = $derived(iconClass === "sc-rail__icon" || iconClass === "sc-notice__icon"
    ? icons[name].replace("<svg ", `<svg class="${iconClass}" `)
    : icons[name]);
</script>

{@html markup}
