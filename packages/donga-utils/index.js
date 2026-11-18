'use strict';

/**
 * 이름에 대한 인사말을 반환한다. (Python donga_app.main.greet과 같은 규칙)
 * 앞뒤 공백은 제거하며, 문자열이 아니면 TypeError, 비어 있으면 Error를 던진다.
 */
function greet(name = 'world') {
  if (typeof name !== 'string') {
    throw new TypeError('name must be a string');
  }
  const trimmed = name.trim();
  if (!trimmed) {
    throw new Error('name must not be empty');
  }
  return `Hello, ${trimmed}!`;
}

module.exports = { greet };
