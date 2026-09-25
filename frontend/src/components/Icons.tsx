import {
  ArrowRight,
  ArrowsClockwise,
  Backspace,
  CaretLeft,
  Check,
  HandHeart,
  Star,
  User,
  WarningCircle,
  WifiSlash,
  type Icon,
} from "@phosphor-icons/react";

type P = { className?: string };
const base = "h-6 w-6";

// Peso único para o projeto inteiro: "bold" lê melhor à distância no tablet da recepção.
const wrap = (I: Icon) => ({ className = base }: P) => <I className={className} weight="bold" aria-hidden />;

export const IconStar = wrap(Star);
export const IconPreferencial = wrap(HandHeart);
export const IconUser = wrap(User);
export const IconCheck = wrap(Check);
export const IconAlert = wrap(WarningCircle);
export const IconBack = wrap(CaretLeft);
export const IconBackspace = wrap(Backspace);
export const IconRefresh = wrap(ArrowsClockwise);
export const IconWifiOff = wrap(WifiSlash);
export const IconArrowRight = wrap(ArrowRight);
