export const somenteDigitos = (v: string) => v.replace(/\D/g, "").slice(0, 11);

export function formatarCpf(digitos: string): string {
  const d = somenteDigitos(digitos);
  const p = [d.slice(0, 3), d.slice(3, 6), d.slice(6, 9), d.slice(9, 11)];
  let out = p[0];
  if (d.length > 3) out += "." + p[1];
  if (d.length > 6) out += "." + p[2];
  if (d.length > 9) out += "-" + p[3];
  return out;
}

export function cpfValido(valor: string): boolean {
  const d = somenteDigitos(valor);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  for (const len of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < len; i++) soma += Number(d[i]) * (len + 1 - i);
    let dig = (soma * 10) % 11;
    if (dig === 10) dig = 0;
    if (dig !== Number(d[len])) return false;
  }
  return true;
}
