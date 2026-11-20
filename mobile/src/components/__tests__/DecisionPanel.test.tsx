import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import i18n from '@/i18n';

import { DecisionPanel } from '../DecisionPanel';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

test('confirm is a single tap (the screen asks "are you sure?")', async () => {
  const onConfirm = jest.fn();
  await render(<DecisionPanel busy={false} onConfirm={onConfirm} onReason={jest.fn()} />);
  await fireEvent.press(screen.getByTestId('decide-confirm'));
  expect(onConfirm).toHaveBeenCalledTimes(1);
});

test('reject cannot be sent without a reason', async () => {
  const onReason = jest.fn();
  await render(<DecisionPanel busy={false} onConfirm={jest.fn()} onReason={onReason} />);
  await fireEvent.press(screen.getByTestId('decide-reject'));
  expect(screen.getByTestId('reason-form-reject')).toBeTruthy();
  await fireEvent.press(screen.getByTestId('reason-submit'));
  expect(onReason).not.toHaveBeenCalled();
  await fireEvent.changeText(screen.getByTestId('reason-input'), '  Photo   too dark  ');
  await fireEvent.press(screen.getByTestId('reason-submit'));
  expect(onReason).toHaveBeenCalledWith('reject', 'Photo too dark');
});

test('a quick reason can be used for flagging a duplicate', async () => {
  const onReason = jest.fn();
  await render(<DecisionPanel busy={false} onConfirm={jest.fn()} onReason={onReason} />);
  await fireEvent.press(screen.getByTestId('decide-flag'));
  await fireEvent.press(screen.getByTestId('quick-reason-Possible duplicate of a nearby report'));
  await fireEvent.press(screen.getByTestId('reason-submit'));
  expect(onReason).toHaveBeenCalledWith('flag', 'Possible duplicate of a nearby report');
});

test('cancel goes back to the three actions', async () => {
  await render(<DecisionPanel busy={false} onConfirm={jest.fn()} onReason={jest.fn()} />);
  await fireEvent.press(screen.getByTestId('decide-reject'));
  await fireEvent.press(screen.getByText('Cancel'));
  expect(screen.getByTestId('decide-confirm')).toBeTruthy();
});

test('quick reasons are translated into Swahili', async () => {
  await i18n.changeLanguage('sw');
  await render(<DecisionPanel busy={false} onConfirm={jest.fn()} onReason={jest.fn()} />);
  await fireEvent.press(screen.getByTestId('decide-reject'));
  expect(screen.getByText('Si uchafuzi')).toBeTruthy();
});
