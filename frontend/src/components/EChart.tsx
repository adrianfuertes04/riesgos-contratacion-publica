import {
  BarChart,
  GraphChart,
  LineChart,
  MapChart,
  type BarSeriesOption,
  type GraphSeriesOption,
  type LineSeriesOption,
  type MapSeriesOption,
} from "echarts/charts";
import {
  GeoComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  TooltipComponent,
  VisualMapComponent,
  type GeoComponentOption,
  type GridComponentOption,
  type LegendComponentOption,
  type ToolboxComponentOption,
  type TooltipComponentOption,
  type VisualMapComponentOption,
} from "echarts/components";
import * as echarts from "echarts/core";
import type { ComposeOption, ECElementEvent } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

echarts.use([
  BarChart,
  LineChart,
  MapChart,
  GraphChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent,
  VisualMapComponent,
  GeoComponent,
  SVGRenderer,
]);

export type EChartsOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | MapSeriesOption
  | GraphSeriesOption
  | TooltipComponentOption
  | LegendComponentOption
  | GridComponentOption
  | ToolboxComponentOption
  | VisualMapComponentOption
  | GeoComponentOption
>;

export { echarts };
export type { ECElementEvent };

export interface EChartHandle {
  zoom: (factor: number) => void;
  reset: () => void;
}

interface Props {
  option: EChartsOption;
  height?: number;
  onClick?: (params: ECElementEvent) => void;
}

/** Contenedor mínimo de ECharts (importación modular + renderizador SVG para exportar figuras nítidas). */
const EChart = forwardRef<EChartHandle, Props>(function EChart({ option, height = 320, onClick }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const zoomRef = useRef(1);

  useImperativeHandle(
    ref,
    () => ({
      zoom(factor: number) {
        const c = chart.current;
        if (!c) return;
        zoomRef.current = Math.min(6, Math.max(0.3, zoomRef.current * factor));
        c.setOption({ series: [{ zoom: zoomRef.current }] });
      },
      reset() {
        const c = chart.current;
        if (!c) return;
        zoomRef.current = 1;
        c.dispatchAction({ type: "restore" });
      },
    }),
    [],
  );

  useEffect(() => {
    if (!containerRef.current) return;
    chart.current = echarts.init(containerRef.current, undefined, { renderer: "svg" });
    const resize = () => chart.current?.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    zoomRef.current = 1;
    chart.current?.setOption(
      {
        toolbox: { right: 8, feature: { saveAsImage: { title: "Exportar", type: "svg" } } },
        ...option,
      },
      true,
    );
  }, [option]);

  useEffect(() => {
    const c = chart.current;
    if (!c || !onClick) return;
    c.on("click", onClick);
    return () => {
      c.off("click", onClick);
    };
  }, [onClick]);

  return <div ref={containerRef} style={{ height }} className="w-full" />;
});

export default EChart;
