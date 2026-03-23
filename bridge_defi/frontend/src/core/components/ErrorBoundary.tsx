import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  domain: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  public static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(`[${this.props.domain}]`, error, info);
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div role="alert" className="error-boundary">
          <h2>{this.props.domain} unavailable</h2>
          <p>Something went wrong while rendering this section.</p>
        </div>
      );
    }

    return this.props.children;
  }
}
