interface Props {
  variant?: "color" | "white";
  className?: string;
}

export function Logo({ variant = "color", className = "h-14" }: Props) {
  const src = variant === "white" ? "/brand/logo-multilife-white.png" : "/brand/logo-multilife.png";
  return <img src={src} alt="MultiLife, Saúde e Segurança do Trabalho" className={`${className} w-auto`} draggable={false} />;
}

export function BrandMark({ variant = "color", className = "h-10" }: Props & { variant?: "color" | "white" | "blue" | "red" }) {
  const map = { color: "icon", white: "icon-white", blue: "icon-blue", red: "icon-red" } as const;
  return <img src={`/brand/${map[variant]}.png`} alt="" aria-hidden className={`${className} w-auto`} draggable={false} />;
}
