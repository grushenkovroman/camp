// Автоподстановка баллов и причины при выборе категории в форме начисления.
// Подставленные значения можно свободно править перед отправкой.
document.querySelectorAll('.quick-score').forEach(function (form) {
  var category = form.querySelector('select[name="category"]');
  if (!category) return;
  var points = form.querySelector('input[name="points"]');
  var reason = form.querySelector('input[name="reason"]');

  category.addEventListener('change', function () {
    var opt = category.selectedOptions[0];
    if (!opt || !opt.value) {
      points.value = '';
      reason.value = '';
      return;
    }
    points.value = opt.dataset.points;
    reason.value = opt.dataset.name;
  });
});
