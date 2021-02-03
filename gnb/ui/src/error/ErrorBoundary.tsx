import React, {Component} from 'react';

type ErrorBoundaryProps = {
  error: Error,
  errorInfo: string,
  hasError: boolean
}

export default class ErrorBoundary extends Component<any, ErrorBoundaryProps> {

  constructor(props: any) {
    super(props);
    this.state = {} as ErrorBoundaryProps;
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      console.error('Handled by ErrorBoundary: ', this.state.error)
      return <div className="alert alert-warning m-3 text-center" role="alert" style={{'whiteSpace': 'pre'}}>
        {this.state.error.message}
      </div>;
    }
    return this.props.children;
  }
}
