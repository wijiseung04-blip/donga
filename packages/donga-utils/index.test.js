'use strict';

const test = require('node:test');
const assert = require('node:assert');
const { greet } = require('./index');

test('기본 인사말', () => {
  assert.strictEqual(greet(), 'Hello, world!');
});

test('이름 앞뒤 공백 제거', () => {
  assert.strictEqual(greet('  OSS  '), 'Hello, OSS!');
});

test('빈 이름은 오류', () => {
  assert.throws(() => greet('   '), /must not be empty/);
});

test('문자열이 아니면 TypeError', () => {
  assert.throws(() => greet(42), TypeError);
});
