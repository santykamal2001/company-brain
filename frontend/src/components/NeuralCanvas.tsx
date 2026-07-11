import { useEffect, useRef } from "react";

interface Props {
  style?: React.CSSProperties;
  primaryRgb?: string;
  opacity?: number;
}

export default function NeuralCanvas({
  style,
  primaryRgb = "14,140,121",
  opacity = 1,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const N = 46;
    const LINK = 160;

    type Node = { x: number; y: number; vx: number; vy: number; r: number; hub: boolean };
    let nodes: Node[] = [];

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      nodes = Array.from({ length: N }, () => ({
        x: Math.random() * canvas.offsetWidth,
        y: Math.random() * canvas.offsetHeight,
        vx: (Math.random() - 0.5) * 0.38,
        vy: (Math.random() - 0.5) * 0.38,
        r: Math.random() < 0.15 ? 4 : 2.5,
        hub: Math.random() < 0.15,
      }));
    };

    resize();

    const signals: { from: Node; to: Node; t: number }[] = [];
    let frame = 0;

    const tick = () => {
      animId = requestAnimationFrame(tick);
      frame++;
      const W = canvas.offsetWidth;
      const H = canvas.offsetHeight;
      ctx.clearRect(0, 0, W, H);

      // edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < LINK) {
            const a = ((1 - d / LINK) * 0.28 * opacity).toFixed(3);
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(${primaryRgb},${a})`;
            ctx.lineWidth = 0.75;
            ctx.stroke();
          }
        }
      }

      // spawn signals
      if (frame % 55 === 0 && nodes.length > 1) {
        const i = Math.floor(Math.random() * nodes.length);
        let j = i;
        while (j === i) j = Math.floor(Math.random() * nodes.length);
        signals.push({ from: nodes[i], to: nodes[j], t: 0 });
      }

      // draw signals
      for (let s = signals.length - 1; s >= 0; s--) {
        signals[s].t += 0.016;
        if (signals[s].t >= 1) { signals.splice(s, 1); continue; }
        const { from, to, t } = signals[s];
        const sx = from.x + (to.x - from.x) * t;
        const sy = from.y + (to.y - from.y) * t;
        const a = ((1 - t) * 0.9 * opacity).toFixed(3);
        ctx.beginPath();
        ctx.arc(sx, sy, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${primaryRgb},${a})`;
        ctx.fill();
      }

      // nodes
      nodes.forEach((n) => {
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > W) n.vx *= -1;
        if (n.y < 0 || n.y > H) n.vy *= -1;

        if (n.hub) {
          const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 4);
          grd.addColorStop(0, `rgba(${primaryRgb},${(0.45 * opacity).toFixed(3)})`);
          grd.addColorStop(1, `rgba(${primaryRgb},0)`);
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r * 4, 0, Math.PI * 2);
          ctx.fillStyle = grd;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${primaryRgb},${(n.hub ? 0.75 : 0.45) * opacity})`;
        ctx.fill();
      });
    };

    tick();

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(animId);
      ro.disconnect();
    };
  }, [primaryRgb, opacity]);

  return (
    <canvas
      ref={canvasRef}
      style={{ display: "block", width: "100%", height: "100%", ...style }}
    />
  );
}
