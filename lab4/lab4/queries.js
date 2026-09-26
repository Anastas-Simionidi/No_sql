// 1. Фильтрация ($match)
db.products.aggregate([{ $match: { category: "Notebook", price: { $lte: 500000 } } }]);

// 2. Проекция и вычисляемые поля ($project)
db.products.aggregate([
  { $match: { category: "Notebook" } },
  { $project: { _id: 0, name: 1, price: 1, stock: 1, inventoryValue: { $multiply: ["$price", "$stock"] } } }
]);

// 3. Группировка ($group)
db.products.aggregate([
  { $group: { _id: "$category", avgPrice: { $avg: "$price" }, productCount: { $sum: 1 } } }
]);

// 4. Сортировка и лимит ($sort, $limit)
db.products.aggregate([
  { $match: { stock: { $gt: 0 } } },
  { $sort: { price: -1 } },
  { $limit: 3 },
  { $project: { _id: 0, name: 1, price: 1 } }
]);

// 5. Работа с массивами ($unwind)
db.products.aggregate([
  { $unwind: "$tags" },
  { $group: { _id: "$tags", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
]);

// 6. Объединение коллекций ($lookup)
db.orders.aggregate([
  { $lookup: { from: "customers", localField: "customerId", foreignField: "customerId", as: "customer" } },
  { $unwind: "$customer" },
  { $project: { _id: 0, orderId: 1, total: 1, "customer.name": 1 } }
]);

// 7. Анализ производительности и индексы (explain)
db.products.find({ category: "Notebook" }).explain("executionStats");
db.products.createIndex({ category: 1 });
db.products.find({ category: "Notebook" }).explain("executionStats");