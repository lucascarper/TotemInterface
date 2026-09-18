import { Component, type ErrorInfo, type ReactNode } from "react";
import { Logo } from "./Logo";

interface Props {
  children: ReactNode;
}

interface State {
  erro: Error | null;
}

/**
 * Última linha de defesa: sem isto, qualquer exceção não tratada durante o
 * render (ex.: API respondendo algo inesperado, um dado em formato errado)
 * derruba a árvore inteira do React e deixa a tela completamente branca,
 * sem nenhuma pista do que aconteceu.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { erro: null };

  static getDerivedStateFromError(erro: Error): State {
    return { erro };
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    console.error("Erro não tratado na interface:", erro, info.componentStack);
  }

  render() {
    if (!this.state.erro) return this.props.children;
    return (
      <div className="grid min-h-[100dvh] place-items-center bg-surface-alt px-6 text-center">
        <div className="w-full max-w-sm">
          <Logo className="mx-auto h-10" />
          <h1 className="mt-6 text-xl font-bold text-ink">Algo deu errado</h1>
          <p className="mt-2 text-sm text-ink-muted">
            A tela travou por um erro inesperado. Tente recarregar a página.
          </p>
          {import.meta.env.DEV && (
            <pre className="mt-4 max-h-40 overflow-auto rounded-lg bg-white p-3 text-left text-xs text-brand-red">
              {this.state.erro.message}
            </pre>
          )}
          <button
            onClick={() => window.location.reload()}
            className="btn-primary mt-6 px-6 py-2.5"
          >
            Recarregar
          </button>
        </div>
      </div>
    );
  }
}
