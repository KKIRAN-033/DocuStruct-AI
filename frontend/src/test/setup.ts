import '@testing-library/jest-dom';

// Mock HTMLCanvasElement.prototype.getContext for axe-core in JSDOM
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = () => null;
}
